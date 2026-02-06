"""
Modèles de données pour les tickets Zammad.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from app.database import Base


# Modèle Pydantic pour les tickets (API)
class Ticket(BaseModel):
    """
    Modèle Pydantic pour les tickets Zammad.
    Utilisé pour la sérialisation/désérialisation des données API.
    """
    id: int
    title: str
    state: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    close_at: Optional[datetime] = None
    priority: str = "normal"
    
    class Config:
        from_attributes = True


class TicketStats(BaseModel):
    """
    Modèle pour les statistiques de tickets (histogramme).
    """
    date: str  # Format YYYY-MM-DD
    count: int
    
    class Config:
        from_attributes = True


# Modèle SQLAlchemy pour le cache local (optionnel)
class TicketCache(Base):
    """
    Cache local des tickets Zammad pour améliorer les performances.
    Synchronisé périodiquement avec l'API Zammad.
    """
    __tablename__ = "ticket_cache"
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    state = Column(String(50))
    tags = Column(PG_ARRAY(String), default=[])
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    close_at = Column(DateTime, nullable=True, index=True)
    priority = Column(String(50))
    synced_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TicketCache(id={self.id}, title='{self.title}', state='{self.state}')>"
    
    def to_pydantic(self) -> Ticket:
        """
        Convertit le modèle SQLAlchemy en modèle Pydantic.
        
        Returns:
            Ticket: Instance Pydantic
        """
        return Ticket(
            id=self.id,
            title=self.title,
            state=self.state,
            tags=self.tags or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
            close_at=self.close_at,
            priority=self.priority
        )
