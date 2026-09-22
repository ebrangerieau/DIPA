"""
Schémas des contrats.
"""
from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal["licence", "maintenance", "telecom", "cloud", "materiel", "service", "autre"]
Decision = Literal["pending", "renew", "renegotiate", "terminate"]
ComputedStatus = Literal["active", "in_notice", "expired"]


def _clean_url(value: Optional[str]) -> Optional[str]:
    """N'accepte que des liens http(s) : un lien javascript: serait exécuté au clic."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.lower().startswith(("https://", "http://")):
        raise ValueError("Le lien doit commencer par https://")
    return value


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ContractFields(BaseModel):
    """Champs saisis d'un contrat (création complète)."""
    name: str = Field(min_length=1, max_length=255)
    supplier: str = Field(min_length=1, max_length=255)
    category: Category = "autre"
    amount: float = Field(ge=0, le=99_999_999.99, description="Montant total du contrat (€)")
    duration_months: int = Field(ge=1, le=240, description="Durée du contrat en mois")
    start_date: date
    end_date: date
    notice_period_days: int = Field(ge=0, le=3650)
    auto_renewal: bool = False
    sharepoint_file_url: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=5000)

    @field_validator("name", "supplier", mode="before")
    @classmethod
    def _strip(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("sharepoint_file_url")
    @classmethod
    def _url(cls, value):
        return _clean_url(value)

    @field_validator("notes")
    @classmethod
    def _notes(cls, value):
        return _clean_text(value)

    @model_validator(mode="after")
    def _check_dates(self):
        if self.end_date <= self.start_date:
            raise ValueError("La date de fin doit être postérieure à la date de début")
        return self


class ContractCreate(ContractFields):
    """Schéma pour la création d'un contrat."""


class ContractUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs transmis sont modifiés."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    supplier: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[Category] = None
    amount: Optional[float] = Field(default=None, ge=0, le=99_999_999.99)
    duration_months: Optional[int] = Field(default=None, ge=1, le=240)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notice_period_days: Optional[int] = Field(default=None, ge=0, le=3650)
    auto_renewal: Optional[bool] = None
    sharepoint_file_url: Optional[str] = Field(default=None, max_length=2000)
    notes: Optional[str] = Field(default=None, max_length=5000)


class ContractOut(BaseModel):
    """Contrat renvoyé par l'API, avec les valeurs calculées."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    supplier: str
    category: str
    category_label: str
    amount: float
    duration_months: int
    start_date: date
    end_date: date
    notice_period_days: int
    auto_renewal: bool
    sharepoint_file_url: Optional[str]
    notes: Optional[str]
    renewal_decision: str
    decision_label: str
    decision_comment: Optional[str]
    decision_by: Optional[str]
    decision_at: Optional[datetime]
    notice_start_date: date
    termination_deadline: date
    days_until_end: int
    days_until_deadline: int
    is_in_notice_period: bool
    is_expired: bool
    computed_status: ComputedStatus
    timeline_color: str
    annual_cost: float
    duration_years: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class DecisionIn(BaseModel):
    decision: Decision
    comment: Optional[str] = Field(default=None, max_length=2000)


class RenewIn(BaseModel):
    """Renouvellement : nouvelle période démarrant le lendemain de l'échéance actuelle."""
    amount: Optional[float] = Field(default=None, ge=0, le=99_999_999.99)
    duration_months: Optional[int] = Field(default=None, ge=1, le=240)
    notice_period_days: Optional[int] = Field(default=None, ge=0, le=3650)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ContractEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    event_label: str
    details: Optional[dict]
    username: Optional[str]
    created_at: datetime
