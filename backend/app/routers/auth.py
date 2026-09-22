"""
Router d'authentification : comptes locaux et SSO Microsoft Entra ID.
"""
import logging
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import security, timeutils
from app.auth import (
    clear_session_cookie,
    client_ip,
    get_current_user,
    set_session_cookie,
)
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import LoginRateLimiter
from app.schemas.users import AuthConfig, LoginResponse, PasswordChange, UserOut
from app.services import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentification"])

login_limiter = LoginRateLimiter(settings.login_max_attempts, settings.login_lockout_minutes * 60)

SSO_FLOW_COOKIE = "cockpit_sso_flow"
SSO_FLOW_TTL = timedelta(minutes=10)
SSO_COOKIE_PATH = "/api/auth"


@router.get("/config", response_model=AuthConfig)
def auth_config():
    """Modes de connexion disponibles (affichés sur la page de connexion)."""
    return AuthConfig(
        app_name=settings.app_name,
        app_version=settings.app_version,
        local_enabled=settings.enable_local_auth,
        sso_enabled=settings.sso_enabled,
    )


# ========== AUTHENTIFICATION LOCALE ==========

@router.post("/login/local", response_model=LoginResponse)
def login_local(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Connexion par identifiant (ou e-mail) et mot de passe.
    Pose le cookie de session httpOnly ; le jeton est aussi renvoyé pour Swagger.
    """
    if not settings.enable_local_auth:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="L'authentification locale est désactivée")

    # Limitation par identifiant : derrière deux reverse proxies, l'IP transmise
    # (X-Forwarded-For) peut être falsifiée et ne constitue pas une clé fiable.
    limiter_key = form_data.username.strip().lower()
    retry_after = login_limiter.retry_after(limiter_key)
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de tentatives. Réessayez dans {max(1, retry_after // 60)} minute(s).",
            headers={"Retry-After": str(retry_after)},
        )

    user = user_service.find_by_login(db, form_data.username)
    if user is None or not user.has_local_password:
        security.burn_password_check()
        valid = False
    else:
        valid = user.verify_password(form_data.password)
    if not valid:
        login_limiter.register_failure(limiter_key)
        logger.warning("Échec de connexion locale pour « %s » depuis %s", form_data.username, client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")
    if security.is_compromised_password(form_data.password):
        # Mot de passe publié (dépôt public) : n'importe qui pourrait l'utiliser, connexion bloquée
        logger.warning("Connexion bloquée pour « %s » : mot de passe publié", user.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce mot de passe a été publié et n'est plus accepté. "
                   "Un administrateur doit le réinitialiser (scripts/create_admin.py).",
        )

    login_limiter.reset(limiter_key)
    # Mot de passe trop faible ou publié : changement imposé dès la connexion
    if security.password_policy_error(form_data.password):
        user.must_change_password = True
    user.last_login = timeutils.utcnow()
    db.commit()
    db.refresh(user)

    token = security.create_access_token(user)
    set_session_cookie(response, token)
    return LoginResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """Supprime le cookie de session."""
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Profil de l'utilisateur connecté."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Changement de son propre mot de passe (comptes locaux). Les autres sessions sont fermées."""
    if not current_user.has_local_password:
        raise HTTPException(status_code=400, detail="Ce compte se connecte avec Microsoft : pas de mot de passe local")
    if not current_user.verify_password(payload.current_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    error = security.password_policy_error(payload.new_password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit être différent de l'actuel")

    current_user.hashed_password = User.hash_password(payload.new_password)
    current_user.must_change_password = False
    current_user.revoke_sessions()
    db.commit()
    set_session_cookie(response, security.create_access_token(current_user))


# ========== AUTHENTIFICATION SSO (MICROSOFT ENTRA ID) ==========

def _frontend_redirect(path: str = "/", **params) -> RedirectResponse:
    base = settings.frontend_url.rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(url=f"{base}{path}{query}", status_code=status.HTTP_302_FOUND)


@router.get("/login")
def sso_login():
    """Redirige vers Microsoft Entra ID (flux authorization code + PKCE)."""
    if not settings.sso_enabled:
        return _frontend_redirect("/login", error="sso_indisponible")

    from app.services.graph_service import GraphService, SSOError

    try:
        flow = GraphService().initiate_login()
    except SSOError:
        return _frontend_redirect("/login", error="sso_indisponible")
    except Exception:
        logger.exception("Initialisation du SSO impossible")
        return _frontend_redirect("/login", error="sso_indisponible")

    auth_uri = flow.pop("auth_uri")
    response = RedirectResponse(url=auth_uri, status_code=status.HTTP_302_FOUND)
    # Le flux (state, nonce, code_verifier) est conservé dans un cookie signé et éphémère
    response.set_cookie(
        SSO_FLOW_COOKIE,
        security.encode_signed({"flow": flow}, "sso_flow", SSO_FLOW_TTL),
        max_age=int(SSO_FLOW_TTL.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure_effective,
        samesite="lax",
        path=SSO_COOKIE_PATH,
    )
    return response


@router.get("/callback")
def sso_callback(request: Request, db: Session = Depends(get_db)):
    """Retour de Microsoft : validation, création/mise à jour du compte, ouverture de session."""
    from app.services.graph_service import GraphService, SSOError

    flow_token = request.cookies.get(SSO_FLOW_COOKIE)
    if not flow_token:
        return _frontend_redirect("/login", error="session_expiree")
    try:
        flow = security.decode_signed(flow_token, "sso_flow")["flow"]
        claims = GraphService().complete_login(flow, dict(request.query_params))
        user = user_service.provision_sso_user(db, claims)
    except (security.TokenError, KeyError):
        return _frontend_redirect("/login", error="session_expiree")
    except user_service.AccessDenied as exc:
        logger.warning("Connexion SSO refusée : %s", exc)
        return _frontend_redirect("/login", error="acces_refuse")
    except SSOError:
        return _frontend_redirect("/login", error="sso_echec")

    if not user.is_active:
        response = _frontend_redirect("/login", error="compte_en_attente")
    else:
        response = _frontend_redirect("/")
        set_session_cookie(response, security.create_access_token(user))
    response.delete_cookie(SSO_FLOW_COOKIE, path=SSO_COOKIE_PATH)
    return response
