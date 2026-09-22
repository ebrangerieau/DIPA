"""
Historique des actions sur les contrats (traçabilité : qui a fait quoi et quand).
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Uuid

from app import timeutils
from app.database import Base

EVENT_LABELS = {
    "created": "Création",
    "updated": "Modification",
    "deleted": "Suppression",
    "decision": "Décision de renouvellement",
    "renewed": "Renouvellement",
    "auto_renewed": "Reconduction tacite automatique",
    "restored": "Restauration depuis une sauvegarde",
}


class ContractEvent(Base):
    __tablename__ = "contract_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Uuid, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    contract_name = Column(String(255), nullable=False)  # Conservé même après suppression
    event_type = Column(String(30), nullable=False)
    details = Column(JSON, nullable=True)
    username = Column(String(255), nullable=True)  # None = action automatique
    created_at = Column(DateTime, default=timeutils.utcnow, nullable=False, index=True)

    @property
    def event_label(self) -> str:
        return EVENT_LABELS.get(self.event_type, self.event_type)
