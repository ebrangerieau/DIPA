"""
Faux serveur Zammad (httpx.MockTransport) reproduisant le comportement observé :
pagination à 200 résultats, états personnalisés, utilisateurs, tags.
"""
from typing import Callable, Optional

import httpx

from app.services.zammad_service import ZammadService

STATES = [
    {"name": "new", "state_type_id": 1, "active": True},
    {"name": "open", "state_type_id": 2, "active": True},
    {"name": "En attente de livraison", "state_type_id": 2, "active": True},
    {"name": "pending reminder", "state_type_id": 3, "active": True},
    {"name": "closed", "state_type_id": 5, "active": True},
    {"name": "merged", "state_type_id": 6, "active": True},
]

USERS = {
    1: {"id": 1, "login": "-", "firstname": "-", "lastname": ""},
    10: {"id": 10, "login": "tech1@exemple.test", "firstname": "Alice", "lastname": "Martin"},
    11: {"id": 11, "login": "tech2@exemple.test", "firstname": "Bruno", "lastname": "Petit"},
}


def ticket(
    ticket_id: int,
    *,
    state: str = "open",
    created_at: str = "2026-09-01T08:00:00Z",
    close_at: Optional[str] = None,
    last_close_at: Optional[str] = None,
    owner_id: int = 10,
    title: Optional[str] = None,
    priority: str = "2 normal",
) -> dict:
    return {
        "id": ticket_id,
        "number": str(20000 + ticket_id),
        "title": title or f"Ticket {ticket_id}",
        "state": state,
        "priority": priority,
        "created_at": created_at,
        "updated_at": created_at,
        "close_at": close_at,
        "last_close_at": last_close_at or close_at,
        "owner_id": owner_id,
        "owner": USERS.get(owner_id, {}).get("login"),
        "group": "Support",
    }


class FakeZammad:
    def __init__(self, search: Callable[[str], list], status_code: Optional[int] = None, tags: Optional[dict] = None):
        self.search = search
        self.status_code = status_code
        self.tags = tags or {}
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status_code:
            return httpx.Response(self.status_code, json={"error": "refusé"})
        path = request.url.path
        params = request.url.params
        if path == "/api/v1/ticket_states":
            return httpx.Response(200, json=STATES)
        if path == "/api/v1/users/me":
            return httpx.Response(200, json={"id": 99, "login": "api"})
        if path.startswith("/api/v1/users/"):
            user = USERS.get(int(path.rsplit("/", 1)[1]))
            return httpx.Response(200, json=user) if user else httpx.Response(404)
        if path == "/api/v1/tickets/search":
            page, per_page = int(params["page"]), int(params["per_page"])
            matched = self.search(params["query"])
            return httpx.Response(200, json=matched[(page - 1) * per_page: page * per_page])
        if path == "/api/v1/tags":
            return httpx.Response(200, json={"tags": self.tags.get(int(params["o_id"]), [])})
        if path.startswith("/api/v1/tickets/"):
            ticket_id = int(path.rsplit("/", 1)[1])
            found = [t for t in self.search("*") if t["id"] == ticket_id]
            return httpx.Response(200, json=found[0]) if found else httpx.Response(404)
        return httpx.Response(404)

    def service(self) -> ZammadService:
        return ZammadService(transport=httpx.MockTransport(self.handler))

    def queries(self) -> list[str]:
        return [r.url.params["query"] for r in self.requests if r.url.path == "/api/v1/tickets/search"]
