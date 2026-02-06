"""
Modèle utilisateur pour l'authentification locale.
"""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from passlib.context import CryptContext
import uuid

from app.database import Base

# Configuration du hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    """
    Modèle utilisateur pour l'authentification locale.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def verify_password(self, plain_password: str) -> bool:
        """
        Vérifie si le mot de passe correspond.
        
        Args:
            plain_password: Mot de passe en clair
        
        Returns:
            bool: True si le mot de passe est correct
        """
        return pwd_context.verify(plain_password, self.hashed_password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hache un mot de passe.
        
        Args:
            password: Mot de passe en clair
        
        Returns:
            str: Mot de passe haché
        """
        return pwd_context.hash(password)
