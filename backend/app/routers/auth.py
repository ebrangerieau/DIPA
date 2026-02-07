"""
Router pour l'authentification (locale et SSO avec Microsoft Entra ID).
"""
from fastapi import APIRouter, HTTPException, status, Query, Response, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Dict
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import secrets

from app.services.graph_service import GraphService
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.auth import create_access_token, get_current_user


# Schémas Pydantic pour l'authentification locale
class UserCreate(BaseModel):
    """Schéma pour créer un utilisateur."""
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    is_admin: bool = False


class UserResponse(BaseModel):
    """Réponse utilisateur."""
    id: UUID
    username: str
    email: str
    full_name: str | None
    is_admin: bool
    is_active: bool
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Réponse de login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Schémas Pydantic pour SSO
class UserInfo(BaseModel):
    """Informations utilisateur."""
    id: str
    display_name: str
    email: str
    job_title: str | None = None


class TokenResponse(BaseModel):
    """Réponse contenant le token d'accès."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str | None = None


# Router
router = APIRouter(prefix="/auth", tags=["authentication"])


def get_graph_service() -> GraphService:
    """Dépendance pour obtenir le service Graph."""
    return GraphService()


# Stockage temporaire des états CSRF (en production, utiliser Redis ou une base de données)
_csrf_states: Dict[str, datetime] = {}
_csrf_state_ttl = timedelta(minutes=10)


def _cleanup_csrf_states() -> None:
    """Nettoie les états CSRF expirés."""
    now = datetime.utcnow()
    expired_states = [
        state for state, created_at in _csrf_states.items()
        if now - created_at > _csrf_state_ttl
    ]
    for state in expired_states:
        _csrf_states.pop(state, None)


# ========== AUTHENTIFICATION LOCALE ==========

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Crée un nouvel utilisateur (authentification locale).
    
    Args:
        user_data: Données de l'utilisateur
        db: Session de base de données
    
    Returns:
        UserResponse: Utilisateur créé
    
    Raises:
        HTTPException: Si l'utilisateur existe déjà
    """
    if not settings.enable_local_auth:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'authentification locale est désactivée"
        )

    if user_data.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La création d'un compte administrateur via l'inscription est interdite"
        )

    if len(user_data.password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe doit contenir au moins 12 caractères"
        )
    
    # Vérifier si l'utilisateur existe déjà
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nom d'utilisateur ou email déjà utilisé"
        )
    
    # Créer l'utilisateur
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=User.hash_password(user_data.password),
        full_name=user_data.full_name,
        is_admin=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login/local", response_model=LoginResponse)
async def login_local(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authentification locale avec username/password.
    
    Args:
        form_data: Formulaire OAuth2 (username, password)
        db: Session de base de données
    
    Returns:
        LoginResponse: Token d'accès et informations utilisateur
    
    Raises:
        HTTPException: Si les identifiants sont incorrects
    """
    if not settings.enable_local_auth:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'authentification locale est désactivée"
        )
    
    # Rechercher l'utilisateur
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compte utilisateur inactif"
        )
    
    # Mettre à jour la date de dernière connexion
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Créer le token JWT
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email, "is_admin": user.is_admin}
    )
    
    return LoginResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Récupère le profil de l'utilisateur connecté.
    
    Args:
        current_user: Utilisateur actuel (injecté par dépendance)
    
    Returns:
        UserResponse: Profil utilisateur
    """
    return current_user


# ========== AUTHENTIFICATION SSO (MICROSOFT ENTRA ID) ==========

@router.get("/login")
async def login(graph: GraphService = Depends(get_graph_service)):
    """
    Initie le flux d'authentification SSO.
    Redirige l'utilisateur vers Microsoft Entra ID.
    
    Args:
        graph: Service Graph
    
    Returns:
        RedirectResponse: Redirection vers la page de connexion Microsoft
    """
    # Nettoyage des états expirés
    _cleanup_csrf_states()

    # Génération d'un état CSRF pour sécuriser le callback
    state = secrets.token_urlsafe(32)
    _csrf_states[state] = datetime.utcnow()
    
    # Génération de l'URL d'authentification
    auth_url = graph.get_auth_url(state=state)
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(
    code: str = Query(..., description="Code d'autorisation"),
    state: str = Query(..., description="État CSRF"),
    graph: GraphService = Depends(get_graph_service)
):
    """
    Callback OAuth après authentification.
    Échange le code d'autorisation contre un token d'accès.
    
    Args:
        code: Code d'autorisation reçu de Microsoft
        state: État CSRF pour validation
        graph: Service Graph
    
    Returns:
        TokenResponse: Token d'accès et informations
    
    Raises:
        HTTPException: En cas d'erreur d'authentification
    """
    # Nettoyage des états expirés
    _cleanup_csrf_states()

    # Validation de l'état CSRF
    created_at = _csrf_states.get(state)
    if not created_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="État CSRF invalide"
        )

    if datetime.utcnow() - created_at > _csrf_state_ttl:
        _csrf_states.pop(state, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="État CSRF expiré"
        )
    
    # Suppression de l'état utilisé
    _csrf_states.pop(state, None)
    
    try:
        # Échange du code contre un token
        token_data = await graph.authenticate_user(code)
        
        return TokenResponse(
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erreur d'authentification: {str(e)}"
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user(
    access_token: str = Query(..., description="Token d'accès Microsoft"),
    graph: GraphService = Depends(get_graph_service)
):
    """
    Récupère les informations de l'utilisateur connecté.
    
    Args:
        access_token: Token d'accès Microsoft
        graph: Service Graph
    
    Returns:
        UserInfo: Informations utilisateur
    
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        user_data = await graph.get_user_info(access_token)
        
        return UserInfo(
            id=user_data["id"],
            display_name=user_data.get("displayName", ""),
            email=user_data.get("mail", user_data.get("userPrincipalName", "")),
            job_title=user_data.get("jobTitle")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erreur lors de la récupération des informations utilisateur: {str(e)}"
        )


@router.post("/refresh")
async def refresh_access_token(
    refresh_token: str = Query(..., description="Token de rafraîchissement"),
    graph: GraphService = Depends(get_graph_service)
):
    """
    Rafraîchit le token d'accès.
    
    Args:
        refresh_token: Token de rafraîchissement
        graph: Service Graph
    
    Returns:
        TokenResponse: Nouveau token d'accès
    
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        token_data = graph.refresh_token(refresh_token)
        
        return TokenResponse(
            access_token=token_data["access_token"],
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erreur lors du rafraîchissement du token: {str(e)}"
        )
