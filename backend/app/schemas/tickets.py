"""
Schémas des tickets Zammad.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Ticket(BaseModel):
    """Ticket Zammad simplifié."""
    id: int
    number: Optional[str] = None
    title: str
    state: str
    priority: str = "2 normal"
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    close_at: Optional[datetime] = None
    owner_id: Optional[int] = None
    owner: Optional[str] = None
    group: Optional[str] = None
    url: Optional[str] = None


class TicketStats(BaseModel):
    """Nombre de tickets clos pour une journée (histogramme)."""
    date: str  # Format YYYY-MM-DD
    count: int
