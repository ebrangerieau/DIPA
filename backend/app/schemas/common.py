"""
Schémas partagés.
"""
from typing import Optional

from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    """Élément affiché sur la Smart Timeline."""
    id: str
    type: str  # "contract-milestone" | "contract-notice" | "ticket"
    title: str
    start: str  # Format ISO
    end: Optional[str] = None  # Format ISO (None = jalon)
    color: str
    group: str  # "contracts" | "projects"
    metadata: dict = Field(default_factory=dict)
