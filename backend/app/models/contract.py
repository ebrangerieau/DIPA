"""
Modèle de données pour les contrats.
"""
import uuid
from datetime import date, timedelta

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, Uuid

from app import timeutils
from app.database import Base

# Catégories budgétaires (clé stockée -> libellé affiché)
CATEGORIES = {
    "licence": "Licences logicielles",
    "maintenance": "Maintenance / support",
    "telecom": "Télécom / Internet",
    "cloud": "Hébergement / Cloud",
    "materiel": "Matériel / Location",
    "service": "Prestations de services",
    "autre": "Autre",
}

# Décision de renouvellement prise par l'équipe
DECISIONS = {
    "pending": "À décider",
    "renew": "À reconduire",
    "renegotiate": "À renégocier",
    "terminate": "À résilier",
}

# Couleurs de la timeline (règles du cahier des charges, §4.1)
COLOR_ACTIVE = "#10B981"   # Vert : avant la période de préavis
COLOR_NOTICE = "#F59E0B"   # Orange : préavis, plus de 30 jours avant l'échéance
COLOR_URGENT = "#EF4444"   # Rouge : préavis, 30 jours ou moins avant l'échéance
COLOR_EXPIRED = "#6B7280"  # Gris : expiré
URGENT_THRESHOLD_DAYS = 30


class Contract(Base):
    """
    Modèle SQLAlchemy pour les contrats.
    Représente un contrat avec ses métadonnées et calculs de préavis.
    """
    __tablename__ = "contracts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    supplier = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default="autre", index=True)
    amount = Column(Numeric(10, 2), nullable=False, comment="Montant total du contrat")
    duration_months = Column(Integer, nullable=False, default=12, comment="Durée du contrat en mois")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False, index=True)
    notice_period_days = Column(Integer, nullable=False)
    auto_renewal = Column(Boolean, nullable=False, default=False)
    sharepoint_file_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="active", index=True)  # Historique, le statut réel est calculé
    renewal_decision = Column(String(20), nullable=False, default="pending")
    decision_comment = Column(Text, nullable=True)
    decision_by = Column(String(255), nullable=True)
    decision_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=timeutils.utcnow)
    updated_at = Column(DateTime, default=timeutils.utcnow, onupdate=timeutils.utcnow)

    def __repr__(self):
        return f"<Contract(name='{self.name}', supplier='{self.supplier}', end_date='{self.end_date}')>"

    @property
    def notice_start_date(self) -> date:
        """
        Début de la période de préavis : `end_date - notice_period_days`.
        C'est aussi la date limite pour dénoncer (résilier) le contrat.
        """
        return self.end_date - timedelta(days=self.notice_period_days)

    @property
    def termination_deadline(self) -> date:
        """Date limite de résiliation (alias explicite de notice_start_date)."""
        return self.notice_start_date

    @property
    def days_until_end(self) -> int:
        """Nombre de jours restants jusqu'à l'échéance (négatif si expiré)."""
        return (self.end_date - timeutils.today()).days

    @property
    def days_until_deadline(self) -> int:
        """Nombre de jours restants avant la date limite de résiliation (négatif si dépassée)."""
        return (self.termination_deadline - timeutils.today()).days

    @property
    def is_in_notice_period(self) -> bool:
        """Vérifie si le contrat est dans sa période de préavis."""
        return self.notice_start_date <= timeutils.today() <= self.end_date

    @property
    def is_expired(self) -> bool:
        """Vérifie si le contrat est expiré."""
        return timeutils.today() > self.end_date

    @property
    def computed_status(self) -> str:
        """Statut calculé : "expired", "in_notice" ou "active"."""
        if self.is_expired:
            return "expired"
        if self.is_in_notice_period:
            return "in_notice"
        return "active"

    @property
    def timeline_color(self) -> str:
        """Couleur d'affichage dans la timeline (CDC §4.1)."""
        if self.is_expired:
            return COLOR_EXPIRED
        if self.is_in_notice_period:
            return COLOR_URGENT if self.days_until_end <= URGENT_THRESHOLD_DAYS else COLOR_NOTICE
        return COLOR_ACTIVE

    @property
    def category_label(self) -> str:
        return CATEGORIES.get(self.category or "autre", CATEGORIES["autre"])

    @property
    def decision_label(self) -> str:
        return DECISIONS.get(self.renewal_decision or "pending", DECISIONS["pending"])

    @property
    def annual_cost(self) -> float:
        """Coût annuel moyen du contrat (montant total / nombre d'années)."""
        if not self.duration_months:
            return float(self.amount)
        return float(self.amount) / (self.duration_months / 12)

    @property
    def duration_years(self) -> float:
        """Durée du contrat en années (avec décimales)."""
        return (self.duration_months or 0) / 12
