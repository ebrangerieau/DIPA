"""
Router pour les tickets Zammad.
"""
from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import date, timedelta

from app.services.zammad_service import ZammadService
from app.models.ticket import Ticket, TicketStats
from app.routers.contracts import TimelineItem


router = APIRouter(prefix="/tickets", tags=["tickets"])


def get_zammad_service() -> ZammadService:
    """Dépendance pour obtenir le service Zammad."""
    return ZammadService()


@router.get("/projects", response_model=List[Ticket])
async def get_project_tickets(
    zammad: ZammadService = Depends(get_zammad_service)
):
    """
    Récupère tous les tickets avec le tag #Projet.
    
    Args:
        zammad: Service Zammad
    
    Returns:
        List[Ticket]: Liste des tickets projet
    """
    tickets = await zammad.get_project_tickets()
    return tickets


@router.get("/stats", response_model=List[TicketStats])
async def get_ticket_statistics(
    start_date: date = Query(default=None, description="Date de début (par défaut: 30 jours avant aujourd'hui)"),
    end_date: date = Query(default=None, description="Date de fin (par défaut: aujourd'hui)"),
    exclude_projects: bool = Query(default=True, description="Exclure les tickets #Projet"),
    zammad: ZammadService = Depends(get_zammad_service)
):
    """
    Récupère les statistiques des tickets clos pour l'histogramme.
    
    Args:
        start_date: Date de début de la période
        end_date: Date de fin de la période
        exclude_projects: Si True, exclut les tickets #Projet
        zammad: Service Zammad
    
    Returns:
        List[TicketStats]: Statistiques par jour
    """
    # Valeurs par défaut
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    stats = await zammad.get_closed_tickets_stats(
        start_date=start_date,
        end_date=end_date,
        exclude_project_tag=exclude_projects
    )
    
    return stats


@router.get("/timeline/data", response_model=List[TimelineItem])
async def get_tickets_timeline_data(
    zammad: ZammadService = Depends(get_zammad_service)
):
    """
    Récupère les tickets #Projet formatés pour la timeline.
    
    Args:
        zammad: Service Zammad
    
    Returns:
        List[TimelineItem]: Éléments de timeline pour les tickets
    """
    tickets = await zammad.get_project_tickets()
    timeline_items = []
    
    for ticket in tickets:
        # Utiliser close_at si disponible, sinon la date actuelle pour les tickets ouverts
        end_date = ticket.close_at.isoformat() if ticket.close_at else date.today().isoformat()
        
        item = TimelineItem(
            id=f"ticket-{ticket.id}",
            type="ticket",
            title=ticket.title,
            start=ticket.created_at.isoformat(),
            end=end_date,
            color="#3B82F6",  # Bleu pour les tickets
            metadata={
                "ticket_id": ticket.id,
                "state": ticket.state,
                "priority": ticket.priority,
                "tags": ticket.tags
            }
        )
        timeline_items.append(item)
    
    return timeline_items


@router.get("/{ticket_id}", response_model=Ticket)
async def get_ticket(
    ticket_id: int,
    zammad: ZammadService = Depends(get_zammad_service)
):
    """
    Récupère un ticket spécifique par son ID.
    
    Args:
        ticket_id: ID du ticket Zammad
        zammad: Service Zammad
    
    Returns:
        Ticket: Détails du ticket
    """
    ticket = await zammad.get_ticket_by_id(ticket_id)
    
    if not ticket:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} non trouvé"
        )
    
    return ticket
