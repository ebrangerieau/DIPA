"""
Router du tableau de bord : indicateurs clés (CDC Phase 2) et échéances à traiter.
Les indicateurs contrats restent disponibles même si Zammad est injoignable.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app import timeutils
from app.auth import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.routers.tickets import get_zammad_service
from app.services import contract_service
from app.services.zammad_service import ZammadError, ZammadService

router = APIRouter(prefix="/dashboard", tags=["tableau de bord"])


@router.get("/summary")
async def dashboard_summary(
    horizon_days: int = Query(default=90, ge=7, le=365, description="Horizon de la liste « à traiter »"),
    db: Session = Depends(get_db),
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(get_current_user),
):
    def load_contracts():
        contracts = db.query(Contract).all()
        return (
            contract_service.contract_kpis(contracts, horizon_days),
            contract_service.upcoming_actions(contracts, horizon_days),
        )

    contract_kpis, actions = await run_in_threadpool(load_contracts)

    tickets, tickets_error = None, None
    try:
        tickets = await zammad.get_ticket_kpis()
    except ZammadError as exc:
        tickets_error = str(exc)

    return {
        "generated_at": timeutils.utcnow().isoformat() + "Z",
        "horizon_days": horizon_days,
        "contracts": contract_kpis,
        "actions": actions,
        "tickets": tickets,
        "tickets_error": tickets_error,
    }
