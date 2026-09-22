"""
Router pour la gestion des contrats.
Lecture : tout utilisateur connecté. Création / modification / suppression : administrateurs (CDC §4.3).
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import timeutils
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models.contract import Contract
from app.models.contract_event import ContractEvent
from app.models.user import User
from app.schemas.common import TimelineItem
from app.schemas.contracts import (
    ComputedStatus,
    ContractCreate,
    ContractEventOut,
    ContractFields,
    ContractOut,
    ContractUpdate,
    DecisionIn,
    RenewIn,
)
from app.services import contract_service

router = APIRouter(prefix="/contracts", tags=["contrats"])


def _get_contract(db: Session, contract_id: UUID) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrat introuvable")
    return contract


def _filtered_contracts(
    db: Session,
    status_filter: Optional[str],
    supplier: Optional[str],
    category: Optional[str],
    q: Optional[str],
) -> list[Contract]:
    query = db.query(Contract)
    if supplier:
        query = query.filter(func.lower(Contract.supplier) == supplier.strip().lower())
    if category:
        query = query.filter(Contract.category == category)
    if q:
        pattern = f"%{q.strip().lower()}%"
        query = query.filter(
            func.lower(Contract.name).like(pattern)
            | func.lower(Contract.supplier).like(pattern)
            | func.lower(func.coalesce(Contract.notes, "")).like(pattern)
        )
    contracts = query.order_by(Contract.end_date, Contract.name).all()
    if status_filter:
        # Le statut dépend de la date du jour : filtrage sur la valeur calculée
        contracts = [c for c in contracts if c.computed_status == status_filter]
    return contracts


@router.get("", response_model=list[ContractOut])
def list_contracts(
    status_filter: Optional[ComputedStatus] = Query(default=None, alias="status", description="active | in_notice | expired"),
    supplier: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100, description="Recherche (nom, fournisseur, notes)"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Liste des contrats triés par échéance, avec filtres (CDC §2.3)."""
    return _filtered_contracts(db, status_filter, supplier, category, q)


@router.get("/suppliers", response_model=list[str])
def list_suppliers(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Fournisseurs distincts (listes de filtres)."""
    rows = db.query(Contract.supplier).distinct().all()
    return sorted({r[0] for r in rows}, key=str.lower)


@router.get("/export.csv")
def export_contracts_csv(
    status_filter: Optional[ComputedStatus] = Query(default=None, alias="status"),
    supplier: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Export Excel (CSV ; séparateur point-virgule) de la liste filtrée."""
    contracts = _filtered_contracts(db, status_filter, supplier, category, q)
    filename = f"contrats_{timeutils.today().isoformat()}.csv"
    return Response(
        content=contract_service.contracts_csv(contracts),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timeline/data", response_model=list[TimelineItem])
def get_timeline_data(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Éléments de timeline des contrats selon les règles d'affichage du CDC."""
    return contract_service.timeline_items(db.query(Contract).all())


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_contract(db, contract_id)


@router.get("/{contract_id}/events", response_model=list[ContractEventOut])
def get_contract_events(contract_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Historique des actions sur le contrat (plus récentes d'abord)."""
    return (
        db.query(ContractEvent)
        .filter(ContractEvent.contract_id == contract_id)
        .order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc())
        .all()
    )


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    contract_data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    contract = Contract(**contract_data.model_dump())
    db.add(contract)
    db.flush()
    contract_service.log_event(db, contract, "created", current_user.username)
    db.commit()
    db.refresh(contract)
    return contract


@router.put("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: UUID,
    contract_data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Met à jour les champs transmis ; le contrat résultant est revalidé dans son ensemble."""
    contract = _get_contract(db, contract_id)
    before = contract_service.snapshot(contract)
    merged = {field: getattr(contract, field) for field in ContractFields.model_fields}
    merged["amount"] = float(merged["amount"])
    merged.update(contract_data.model_dump(exclude_unset=True))
    try:
        validated = ContractFields.model_validate(merged)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    for field, value in validated.model_dump().items():
        setattr(contract, field, value)
    changes = contract_service.diff(before, contract_service.snapshot(contract))
    if changes:
        contract_service.log_event(db, contract, "updated", current_user.username, {"changes": changes})
    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    contract = _get_contract(db, contract_id)
    contract_service.log_event(db, contract, "deleted", current_user.username, {"contrat": contract_service.snapshot(contract)})
    db.flush()
    # L'historique est conservé (contract_id mis à NULL) pour garder la trace de la suppression
    db.query(ContractEvent).filter(ContractEvent.contract_id == contract.id).update({"contract_id": None})
    db.delete(contract)
    db.commit()


@router.post("/{contract_id}/decision", response_model=ContractOut)
def set_decision(
    contract_id: UUID,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Enregistre la décision de renouvellement (à reconduire, à renégocier, à résilier)."""
    contract = _get_contract(db, contract_id)
    previous = contract.renewal_decision
    contract.renewal_decision = payload.decision
    contract.decision_comment = (payload.comment or "").strip() or None
    contract.decision_by = current_user.display_name
    contract.decision_at = timeutils.utcnow()
    contract_service.log_event(db, contract, "decision", current_user.username, {
        "avant": previous, "apres": payload.decision, "commentaire": contract.decision_comment,
    })
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/{contract_id}/renew", response_model=ContractOut)
def renew(
    contract_id: UUID,
    payload: RenewIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Renouvelle le contrat : nouvelle période à partir du lendemain de l'échéance."""
    contract = _get_contract(db, contract_id)
    if contract.renewal_decision == "terminate":
        raise HTTPException(status_code=400, detail="La résiliation de ce contrat a été décidée : modifiez d'abord la décision")
    details = contract_service.renew_contract(
        contract,
        amount=payload.amount,
        duration_months=payload.duration_months,
        notice_period_days=payload.notice_period_days,
    )
    if payload.comment:
        details["commentaire"] = payload.comment.strip()
    contract_service.log_event(db, contract, "renewed", current_user.username, details)
    db.commit()
    db.refresh(contract)
    return contract
