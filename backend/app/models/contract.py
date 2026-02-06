"""
Modèle de données pour les contrats.
"""
from sqlalchemy import Column, String, Numeric, Date, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date, timedelta
from app.database import Base
import uuid


class Contract(Base):
    """
    Modèle SQLAlchemy pour les contrats.
    Représente un contrat avec ses métadonnées et calculs de préavis.
    """
    __tablename__ = "contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    supplier = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False, index=True)
    notice_period_days = Column(Integer, nullable=False)
    sharepoint_file_url = Column(Text, nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Contract(name='{self.name}', supplier='{self.supplier}', end_date='{self.end_date}')>"
    
    @property
    def notice_start_date(self) -> date:
        """
        Calcule la date de début de la période de préavis.
        
        Returns:
            date: Date de début du préavis
        """
        return self.end_date - timedelta(days=self.notice_period_days)
    
    @property
    def days_until_end(self) -> int:
        """
        Calcule le nombre de jours restants jusqu'à la fin du contrat.
        
        Returns:
            int: Nombre de jours (négatif si le contrat est expiré)
        """
        today = date.today()
        return (self.end_date - today).days
    
    @property
    def is_in_notice_period(self) -> bool:
        """
        Vérifie si le contrat est dans sa période de préavis.
        
        Returns:
            bool: True si dans la période de préavis
        """
        today = date.today()
        return self.notice_start_date <= today <= self.end_date
    
    @property
    def is_expired(self) -> bool:
        """
        Vérifie si le contrat est expiré.
        
        Returns:
            bool: True si expiré
        """
        return date.today() > self.end_date
    
    @property
    def computed_status(self) -> str:
        """
        Calcule le statut actuel du contrat.
        
        Returns:
            str: "expired", "in_notice", ou "active"
        """
        if self.is_expired:
            return "expired"
        elif self.is_in_notice_period:
            return "in_notice"
        else:
            return "active"
    
    @property
    def timeline_color(self) -> str:
        """
        Détermine la couleur pour l'affichage dans la timeline.
        
        Returns:
            str: Code couleur hexadécimal
        """
        if self.is_expired:
            return "#6B7280"  # Gris
        elif self.is_in_notice_period:
            days_left = self.days_until_end
            if days_left <= 30:
                return "#EF4444"  # Rouge
            else:
                return "#F59E0B"  # Orange
        else:
            return "#10B981"  # Vert
