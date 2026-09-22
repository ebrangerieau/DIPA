"""
Router de gestion des utilisateurs (réservé aux administrateurs).
Remplace l'ancienne inscription publique /auth/register.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import security
from app.auth import require_admin
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.users import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services.user_service import active_admin_count

router = APIRouter(prefix="/users", tags=["utilisateurs"])


def _get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user


def _ensure_not_last_admin(db: Session, user: User) -> None:
    if user.is_admin and user.is_active and active_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Impossible : c'est le dernier administrateur actif")


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return db.query(User).order_by(User.is_active.desc(), func.lower(User.username)).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Crée un compte local. L'utilisateur devra changer son mot de passe à la première connexion."""
    if not settings.enable_local_auth:
        raise HTTPException(status_code=400, detail="Les comptes locaux sont désactivés (SSO uniquement)")
    error = security.password_policy_error(payload.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    duplicate = db.query(User).filter(
        (func.lower(User.username) == payload.username.lower()) | (func.lower(User.email) == payload.email.lower())
    ).first()
    if duplicate:
        raise HTTPException(status_code=400, detail="Identifiant ou e-mail déjà utilisé")

    user = User(
        username=payload.username,
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=User.hash_password(payload.password),
        is_admin=payload.is_admin,
        is_active=True,
        auth_provider="local",
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """Modifie le profil, le rôle ou l'activation d'un compte (validation des comptes SSO)."""
    user = _get_user(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    removing_admin = (data.get("is_admin") is False and user.is_admin) or (data.get("is_active") is False and user.is_active)
    if removing_admin and user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas retirer vos propres droits ni vous désactiver")
    if removing_admin:
        _ensure_not_last_admin(db, user)

    if "email" in data and data["email"]:
        email = data["email"].lower()
        other = db.query(User).filter(func.lower(User.email) == email, User.id != user.id).first()
        if other:
            raise HTTPException(status_code=400, detail="E-mail déjà utilisé")
        user.email = email
    if "full_name" in data:
        user.full_name = data["full_name"]
    if data.get("is_admin") is not None:
        user.is_admin = data["is_admin"]
    if data.get("is_active") is not None:
        if not data["is_active"] and user.is_active:
            user.revoke_sessions()
        user.is_active = data["is_active"]
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: UUID,
    payload: PasswordReset,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Définit un mot de passe temporaire (à changer à la prochaine connexion)."""
    if not settings.enable_local_auth:
        raise HTTPException(status_code=400, detail="Les comptes locaux sont désactivés (SSO uniquement)")
    user = _get_user(db, user_id)
    error = security.password_policy_error(payload.new_password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    user.hashed_password = User.hash_password(payload.new_password)
    user.must_change_password = True
    user.revoke_sessions()
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    user = _get_user(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte")
    _ensure_not_last_admin(db, user)
    db.delete(user)
    db.commit()
