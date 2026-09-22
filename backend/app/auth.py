"""
Dépendances d'authentification et d'autorisation.

Le jeton de session est transmis :
- par un cookie httpOnly pour l'application web (CDC §8 : pas de jeton lisible en JavaScript) ;
- ou par l'en-tête « Authorization: Bearer » (Swagger, scripts d'administration).

Les requêtes modifiantes authentifiées par cookie doivent porter l'en-tête
« X-Requested-With: XMLHttpRequest » : un site tiers ne peut pas l'ajouter sans
autorisation CORS, ce qui protège contre les attaques CSRF.
"""
import time
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.security import TokenError, create_access_token, decode_signed

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-requested-with"
CSRF_HEADER_VALUE = "XMLHttpRequest"
COOKIE_PATH = "/api"

bearer_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/local", auto_error=False)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure_effective,
        samesite="lax",
        path=COOKIE_PATH,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure_effective,
        samesite="lax",
    )


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "inconnu"


def _unauthorized(detail: str = "Authentification requise") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    response: Response,
    bearer_token: Optional[str] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Retourne l'utilisateur authentifié (cookie de session ou jeton Bearer)."""
    token = bearer_token
    from_cookie = False
    if not token:
        token = request.cookies.get(settings.session_cookie_name)
        from_cookie = bool(token)
    if not token:
        raise _unauthorized()

    try:
        payload = decode_signed(token, "access")
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TokenError, ValueError):
        raise _unauthorized("Session invalide ou expirée") from None

    if (
        from_cookie
        and request.method not in SAFE_METHODS
        and request.headers.get(CSRF_HEADER) != CSRF_HEADER_VALUE
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requête refusée (protection CSRF)")

    user = db.get(User, user_id)
    if user is None or not user.is_active or payload.get("ver") != (user.token_version or 0):
        raise _unauthorized("Session invalide ou expirée")

    # Session glissante : le cookie est renouvelé passé la moitié de sa durée de vie
    issued_at = payload.get("iat")
    if from_cookie and issued_at and time.time() - issued_at > settings.access_token_expire_minutes * 30:
        set_session_cookie(response, create_access_token(user))
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Vérifie que l'utilisateur est administrateur (création / modification / suppression)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Droits administrateur requis")
    return current_user
