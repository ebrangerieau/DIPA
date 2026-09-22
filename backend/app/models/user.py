"""
Modèle utilisateur (comptes locaux et comptes Microsoft Entra ID).
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Uuid

from app import security, timeutils
from app.database import Base


class User(Base):
    """Utilisateur de l'application."""
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # None pour les comptes SSO
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    auth_provider = Column(String(20), nullable=False, default="local")  # local | entra
    entra_oid = Column(String(64), unique=True, nullable=True, index=True)
    token_version = Column(Integer, nullable=False, default=0)
    must_change_password = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=timeutils.utcnow)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"

    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @property
    def has_local_password(self) -> bool:
        return bool(self.hashed_password)

    def verify_password(self, plain_password: str) -> bool:
        """Vérifie le mot de passe (toujours faux pour un compte sans mot de passe local)."""
        if not self.hashed_password:
            return False
        return security.verify_password(plain_password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return security.hash_password(password)

    def revoke_sessions(self) -> None:
        """Invalide tous les jetons de session émis pour cet utilisateur."""
        self.token_version = (self.token_version or 0) + 1
