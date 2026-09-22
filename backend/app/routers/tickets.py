"""
Router pour les tickets Zammad (lecture seule, utilisateurs connectés).
Les erreurs Zammad sont renvoyées en 502 avec un message explicite (gestionnaire global).
"""
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app import timeutils
from app.auth import get_current_user
from app.models.user import User
from app.schemas.common import TimelineItem
from app.schemas.tickets import Ticket, TicketStats
from app.services.zammad_service import ZammadService

router = APIRouter(prefix="/tickets", tags=["tickets"])

MAX_STATS_RANGE_DAYS = 400
PROJECT_COLOR = "#3B82F6"  # Bleu (CDC §2.1)


def get_zammad_service() -> ZammadService:
    """Dépendance pour obtenir le service Zammad."""
    return ZammadService()


@router.get("/projects", response_model=list[Ticket])
async def get_project_tickets(
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(get_current_user),
):
    """Tickets portant le tag projet (ZAMMAD_PROJECT_TAG)."""
    return await zammad.get_project_tickets()


@router.get("/stats", response_model=list[TicketStats])
async def get_ticket_statistics(
    start_date: Optional[date] = Query(default=None, description="Date de début (défaut : J-30)"),
    end_date: Optional[date] = Query(default=None, description="Date de fin (défaut : aujourd'hui)"),
    exclude_projects: bool = Query(default=True, description="Exclure les tickets projet"),
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(get_current_user),
):
    """Tickets clos par jour pour l'histogramme et le calendrier d'activité."""
    end_date = end_date or timeutils.today()
    start_date = start_date or end_date - timedelta(days=30)
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="La date de début doit précéder la date de fin")
    if (end_date - start_date).days > MAX_STATS_RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Période limitée à {MAX_STATS_RANGE_DAYS} jours")
    return await zammad.get_closed_tickets_stats(start_date, end_date, exclude_project_tag=exclude_projects)


@router.get("/timeline/data", response_model=list[TimelineItem])
async def get_tickets_timeline_data(
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(get_current_user),
):
    """Tickets projet sous forme de barres bleues (création → clôture, ou aujourd'hui si ouvert)."""
    now = datetime.now(timezone.utc)
    items = []
    for ticket in await zammad.get_project_tickets():
        end = ticket.close_at or now
        items.append(TimelineItem(
            id=f"ticket-{ticket.id}",
            type="ticket",
            title=ticket.title,
            start=ticket.created_at.isoformat(),
            end=max(end, ticket.created_at).isoformat(),
            color=PROJECT_COLOR,
            group="projects",
            metadata={
                "ticket_id": ticket.id,
                "number": ticket.number,
                "title": ticket.title,
                "state": ticket.state,
                "priority": ticket.priority,
                "tags": ticket.tags,
                "owner": ticket.owner,
                "group": ticket.group,
                "created_at": ticket.created_at.isoformat(),
                "close_at": ticket.close_at.isoformat() if ticket.close_at else None,
                "url": ticket.url,
            },
        ))
    return items


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: int,
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(get_current_user),
):
    ticket = await zammad.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} introuvable")
    return ticket
