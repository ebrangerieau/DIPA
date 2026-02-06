"""
Service pour interagir avec l'API Zammad.
"""
import httpx
from typing import List, Dict
from datetime import datetime, date
from collections import defaultdict
from app.config import settings
from app.models.ticket import Ticket, TicketStats


class ZammadService:
    """
    Service pour interagir avec l'API Zammad.
    Gère la récupération des tickets et le calcul des statistiques.
    """
    
    def __init__(self):
        self.api_url = settings.zammad_api_url.rstrip('/')
        self.api_token = settings.zammad_api_token
        self.project_tag = settings.zammad_project_tag
        self.headers = {
            "Authorization": f"Token token={self.api_token}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """
        Effectue une requête HTTP vers l'API Zammad.
        
        Args:
            endpoint: Endpoint de l'API (ex: "/api/v1/tickets")
            params: Paramètres de requête optionnels
        
        Returns:
            Dict: Réponse JSON de l'API
        
        Raises:
            httpx.HTTPError: En cas d'erreur HTTP
        """
        url = f"{self.api_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def get_project_tickets(self) -> List[Ticket]:
        """
        Récupère tous les tickets avec le tag #Projet.
        
        Returns:
            List[Ticket]: Liste des tickets projet
        """
        # Recherche des tickets avec le tag spécifique
        search_query = f"tags:{self.project_tag}"
        params = {
            "query": search_query,
            "limit": 1000,  # Ajuster selon les besoins
            "expand": "true"
        }
        
        try:
            data = await self._make_request("/api/v1/tickets/search", params)
            
            tickets = []
            for ticket_data in data.get("assets", {}).get("Ticket", {}).values():
                # Conversion des dates
                created_at = datetime.fromisoformat(ticket_data["created_at"].replace("Z", "+00:00"))
                updated_at = datetime.fromisoformat(ticket_data["updated_at"].replace("Z", "+00:00"))
                close_at = None
                if ticket_data.get("close_at"):
                    close_at = datetime.fromisoformat(ticket_data["close_at"].replace("Z", "+00:00"))
                
                ticket = Ticket(
                    id=ticket_data["id"],
                    title=ticket_data["title"],
                    state=ticket_data.get("state", "unknown"),
                    tags=ticket_data.get("tags", []),
                    created_at=created_at,
                    updated_at=updated_at,
                    close_at=close_at,
                    priority=ticket_data.get("priority", "normal")
                )
                tickets.append(ticket)
            
            return tickets
        
        except httpx.HTTPError as e:
            print(f"Erreur lors de la récupération des tickets projet: {e}")
            return []
    
    async def get_closed_tickets_stats(
        self, 
        start_date: date, 
        end_date: date,
        exclude_project_tag: bool = True
    ) -> List[TicketStats]:
        """
        Récupère les statistiques des tickets clos pour l'histogramme.
        Exclut les tickets avec le tag #Projet par défaut.
        
        Args:
            start_date: Date de début de la période
            end_date: Date de fin de la période
            exclude_project_tag: Si True, exclut les tickets #Projet
        
        Returns:
            List[TicketStats]: Statistiques par jour
        """
        # Construction de la requête de recherche
        search_query = f"state:closed AND close_at:[{start_date.isoformat()} TO {end_date.isoformat()}]"
        if exclude_project_tag:
            search_query += f" AND NOT tags:{self.project_tag}"
        
        params = {
            "query": search_query,
            "limit": 10000,  # Grande limite pour les statistiques
            "expand": "true"
        }
        
        try:
            data = await self._make_request("/api/v1/tickets/search", params)
            
            # Comptage par jour
            daily_counts = defaultdict(int)
            for ticket_data in data.get("assets", {}).get("Ticket", {}).values():
                if ticket_data.get("close_at"):
                    close_date = datetime.fromisoformat(
                        ticket_data["close_at"].replace("Z", "+00:00")
                    ).date()
                    daily_counts[close_date.isoformat()] += 1
            
            # Conversion en liste de TicketStats
            stats = [
                TicketStats(date=date_str, count=count)
                for date_str, count in sorted(daily_counts.items())
            ]
            
            return stats
        
        except httpx.HTTPError as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            return []
    
    async def get_ticket_by_id(self, ticket_id: int) -> Ticket | None:
        """
        Récupère un ticket spécifique par son ID.
        
        Args:
            ticket_id: ID du ticket
        
        Returns:
            Ticket | None: Le ticket ou None si non trouvé
        """
        try:
            data = await self._make_request(f"/api/v1/tickets/{ticket_id}")
            
            created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
            close_at = None
            if data.get("close_at"):
                close_at = datetime.fromisoformat(data["close_at"].replace("Z", "+00:00"))
            
            return Ticket(
                id=data["id"],
                title=data["title"],
                state=data.get("state", "unknown"),
                tags=data.get("tags", []),
                created_at=created_at,
                updated_at=updated_at,
                close_at=close_at,
                priority=data.get("priority", "normal")
            )
        
        except httpx.HTTPError as e:
            print(f"Erreur lors de la récupération du ticket {ticket_id}: {e}")
            return None
