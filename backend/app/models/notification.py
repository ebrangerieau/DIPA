"""
Journal des alertes envoyées : garantit qu'une même alerte n'est envoyée qu'une fois.
"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid

from app import timeutils
from app.database import Base


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("contract_id", "kind", "reference_date", name="uq_notification_once"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Uuid, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)          # ex. "deadline_30", "end_30"
    reference_date = Column(Date, nullable=False)      # Date d'échéance concernée
    sent_at = Column(DateTime, default=timeutils.utcnow, nullable=False)
