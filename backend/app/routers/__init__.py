"""
Routers de l'application Cockpit IT.
"""
from app.routers.contracts import router as contracts_router
from app.routers.tickets import router as tickets_router
from app.routers.auth import router as auth_router

__all__ = ["contracts_router", "tickets_router", "auth_router"]
