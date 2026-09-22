"""
Gestion des comptes : provisionnement SSO et garde-fous sur les administrateurs.
"""
import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import timeutils
from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)


class AccessDenied(Exception):
    """Compte Microsoft authentifié mais non autorisé à utiliser l'application."""


def active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.is_admin.is_(True), User.is_active.is_(True)).count()


def find_by_login(db: Session, login: str) -> Optional[User]:
    """Recherche par identifiant ou e-mail, sans tenir compte de la casse."""
    login = login.strip().lower()
    return (
        db.query(User)
        .filter((func.lower(User.username) == login) | (func.lower(User.email) == login))
        .first()
    )


def _unique_username(db: Session, wanted: str) -> str:
    base = wanted[:100]
    candidate, index = base, 1
    while db.query(User).filter(func.lower(User.username) == candidate.lower()).first():
        index += 1
        suffix = f"-{index}"
        candidate = base[: 100 - len(suffix)] + suffix
    return candidate


def provision_sso_user(db: Session, claims: dict) -> User:
    """
    Crée ou met à jour le compte associé à une identité Microsoft Entra ID.

    - Tenant vérifié (défense en profondeur, l'autorité est déjà mono-tenant) ;
    - Rôles d'application Entra : SSO_ALLOWED_ROLES (accès) et SSO_ADMIN_ROLES (admin) ;
    - Nouveau compte actif seulement si SSO_AUTO_ACTIVATE=true ou admin désigné,
      sinon il attend la validation d'un administrateur.
    """
    oid = claims.get("oid")
    if settings.azure_tenant_id and str(claims.get("tid", "")).lower() != settings.azure_tenant_id.strip().lower():
        raise AccessDenied("Compte Microsoft d'une autre organisation")

    roles = set(claims.get("roles") or [])
    if settings.sso_allowed_roles and not roles & set(settings.sso_allowed_roles):
        raise AccessDenied("Aucun rôle d'application autorisé")

    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not email:
        raise AccessDenied("Adresse e-mail absente du jeton Microsoft")
    admin_emails = {e.lower() for e in settings.sso_admin_emails}
    designated_admin = email in admin_emails or bool(roles & set(settings.sso_admin_roles))

    user = db.query(User).filter(User.entra_oid == oid).first()
    if user is None:
        # Rattachement d'un compte existant portant la même adresse (migration local -> SSO)
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user is not None and user.entra_oid and user.entra_oid != oid:
            raise AccessDenied("Adresse déjà associée à une autre identité Microsoft")

    if user is None:
        user = User(
            username=_unique_username(db, email),
            email=email,
            hashed_password=None,
            full_name=claims.get("name"),
            is_admin=designated_admin,
            is_active=settings.sso_auto_activate or designated_admin,
            auth_provider="entra",
            entra_oid=oid,
        )
        db.add(user)
        logger.info("Compte SSO créé : %s (actif=%s, admin=%s)", email, user.is_active, user.is_admin)
    else:
        user.entra_oid = oid
        user.auth_provider = "entra"
        user.full_name = claims.get("name") or user.full_name
        if designated_admin and not user.is_admin:
            user.is_admin = True
            user.is_active = True

    user.last_login = timeutils.utcnow()
    db.commit()
    db.refresh(user)
    return user
