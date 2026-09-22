"""
Règles métier des contrats : historique, renouvellement, reconduction tacite,
indicateurs budgétaires et liste des échéances à traiter.
"""
import csv
import io
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app import timeutils
from app.models.contract import CATEGORIES, Contract
from app.models.contract_event import ContractEvent
from app.schemas.common import TimelineItem

# Champs suivis dans l'historique et exportés dans les sauvegardes
TRACKED_FIELDS = (
    "name", "supplier", "category", "amount", "duration_months", "start_date", "end_date",
    "notice_period_days", "auto_renewal", "sharepoint_file_url", "notes",
    "renewal_decision", "decision_comment",
)
MAX_AUTO_RENEWAL_PERIODS = 50  # Garde-fou : rattrapage de périodes écoulées


def _json_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "quantize"):  # Decimal
        return float(value)
    return value


def snapshot(contract: Contract) -> dict:
    return {field: _json_value(getattr(contract, field)) for field in TRACKED_FIELDS}


def diff(before: dict, after: dict) -> dict:
    """Champs modifiés : {champ: [ancienne valeur, nouvelle valeur]}."""
    return {k: [before.get(k), after.get(k)] for k in after if before.get(k) != after.get(k)}


def log_event(
    db: Session,
    contract: Contract,
    event_type: str,
    username: Optional[str],
    details: Optional[dict] = None,
) -> ContractEvent:
    event = ContractEvent(
        contract_id=contract.id,
        contract_name=contract.name,
        event_type=event_type,
        details=details or None,
        username=username,
    )
    db.add(event)
    return event


# ---------- Renouvellement ----------

def renew_contract(
    contract: Contract,
    amount: Optional[float] = None,
    duration_months: Optional[int] = None,
    notice_period_days: Optional[int] = None,
) -> dict:
    """Démarre la période suivante le lendemain de l'échéance et réinitialise la décision."""
    before = {
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat(),
        "amount": float(contract.amount),
    }
    if duration_months:
        contract.duration_months = duration_months
    if amount is not None:
        contract.amount = amount
    if notice_period_days is not None:
        contract.notice_period_days = notice_period_days
    new_start = contract.end_date + timedelta(days=1)
    contract.start_date = new_start
    contract.end_date = timeutils.period_end(new_start, contract.duration_months)
    contract.renewal_decision = "pending"
    contract.decision_comment = None
    contract.decision_by = None
    contract.decision_at = None
    after = {
        "start_date": contract.start_date.isoformat(),
        "end_date": contract.end_date.isoformat(),
        "amount": float(contract.amount),
    }
    return {"avant": before, "apres": after}


def process_auto_renewals(db: Session, today: Optional[date] = None) -> list[dict]:
    """
    Reconduction tacite : un contrat échu, marqué « reconduction tacite » et non résilié,
    est prolongé automatiquement d'une durée identique (plusieurs fois si nécessaire).
    """
    today = today or timeutils.today()
    renewed = []
    candidates = (
        db.query(Contract)
        .filter(
            Contract.auto_renewal.is_(True),
            Contract.end_date < today,
            Contract.renewal_decision != "terminate",
        )
        .all()
    )
    for contract in candidates:
        first = None
        periods = 0
        while contract.end_date < today and periods < MAX_AUTO_RENEWAL_PERIODS:
            change = renew_contract(contract)
            first = first or change["avant"]
            periods += 1
        details = {"avant": first, "apres": {
            "start_date": contract.start_date.isoformat(),
            "end_date": contract.end_date.isoformat(),
        }, "periodes": periods}
        log_event(db, contract, "auto_renewed", None, details)
        renewed.append({"contract_id": str(contract.id), "name": contract.name, **details})
    if renewed:
        db.commit()
    return renewed


# ---------- Timeline ----------

def timeline_items(contracts: list[Contract]) -> list[TimelineItem]:
    """
    Règles d'affichage du CDC (§2.1) :
    - avant le préavis : jalon vert à la date d'échéance ;
    - pendant le préavis : barre orange (> 30 j avant l'échéance) ou rouge (≤ 30 j) ;
    - après expiration : jalon gris.
    """
    items = []
    for c in contracts:
        metadata = {
            "contract_id": str(c.id),
            "name": c.name,
            "supplier": c.supplier,
            "category": c.category_label,
            "amount": float(c.amount),
            "annual_cost": round(c.annual_cost, 2),
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "notice_period_days": c.notice_period_days,
            "notice_start_date": c.notice_start_date.isoformat(),
            "days_until_end": c.days_until_end,
            "days_until_deadline": c.days_until_deadline,
            "computed_status": c.computed_status,
            "auto_renewal": c.auto_renewal,
            "decision": c.renewal_decision,
            "decision_label": c.decision_label,
            "sharepoint_url": c.sharepoint_file_url,
        }
        if c.is_in_notice_period:
            items.append(TimelineItem(
                id=f"contract-notice-{c.id}",
                type="contract-notice",
                title=f"{c.name} – préavis",
                start=c.notice_start_date.isoformat(),
                end=c.end_date.isoformat(),
                color=c.timeline_color,
                group="contracts",
                metadata=metadata,
            ))
        else:
            items.append(TimelineItem(
                id=f"contract-milestone-{c.id}",
                type="contract-milestone",
                title=f"{c.name} – échéance",
                start=c.end_date.isoformat(),
                end=None,
                color=c.timeline_color,
                group="contracts",
                metadata=metadata,
            ))
    return items


# ---------- Indicateurs et actions ----------

def _action_for(contract: Contract, horizon_days: int) -> Optional[dict]:
    if contract.is_expired:
        return None
    deadline_days = contract.days_until_deadline
    if not contract.is_in_notice_period and deadline_days > horizon_days:
        return None

    if not contract.is_in_notice_period:
        key_date = contract.termination_deadline
        days = deadline_days
        urgency = "critical" if days <= 7 else "high" if days <= 30 else "medium"
        if contract.auto_renewal:
            message = "Date limite pour résilier (sinon reconduction tacite)"
        else:
            message = "Début du préavis : lancer le renouvellement"
    else:
        key_date = contract.end_date
        days = contract.days_until_end
        urgency = "high" if days <= 30 else "medium"
        if contract.renewal_decision == "terminate":
            message = "Fin du contrat (résiliation décidée)"
        elif contract.auto_renewal:
            message = "Reconduction tacite à l'échéance"
        else:
            message = "Échéance : contrat à renouveler ou à clore"

    return {
        "contract_id": str(contract.id),
        "name": contract.name,
        "supplier": contract.supplier,
        "key_date": key_date.isoformat(),
        "days": days,
        "urgency": urgency,
        "message": message,
        "decision": contract.renewal_decision,
        "decision_label": contract.decision_label,
        "needs_decision": contract.renewal_decision == "pending",
        "auto_renewal": contract.auto_renewal,
        "computed_status": contract.computed_status,
        "timeline_color": contract.timeline_color,
        "annual_cost": round(contract.annual_cost, 2),
    }


def upcoming_actions(contracts: list[Contract], horizon_days: int = 90) -> list[dict]:
    """Contrats à traiter : date limite de résiliation proche ou préavis en cours."""
    actions = [a for a in (_action_for(c, horizon_days) for c in contracts) if a]
    return sorted(actions, key=lambda a: (a["key_date"], a["name"]))


def contract_kpis(contracts: list[Contract], horizon_days: int = 90) -> dict:
    live = [c for c in contracts if not c.is_expired]
    by_category: dict = defaultdict(lambda: {"annual_cost": 0.0, "count": 0})
    by_supplier: dict = defaultdict(lambda: {"annual_cost": 0.0, "count": 0})
    for c in live:
        by_category[c.category or "autre"]["annual_cost"] += c.annual_cost
        by_category[c.category or "autre"]["count"] += 1
        by_supplier[c.supplier]["annual_cost"] += c.annual_cost
        by_supplier[c.supplier]["count"] += 1

    actions = upcoming_actions(contracts, horizon_days)
    return {
        "total": len(contracts),
        "active": sum(1 for c in contracts if c.computed_status == "active"),
        "in_notice": sum(1 for c in contracts if c.computed_status == "in_notice"),
        "expired": sum(1 for c in contracts if c.computed_status == "expired"),
        "auto_renewal": sum(1 for c in live if c.auto_renewal),
        "annual_budget": round(sum(c.annual_cost for c in live), 2),
        "committed_amount": round(sum(float(c.amount) for c in live), 2),
        "actions_count": len(actions),
        "pending_decisions": sum(1 for a in actions if a["needs_decision"]),
        "by_category": sorted(
            (
                {"category": k, "label": CATEGORIES.get(k, k), "annual_cost": round(v["annual_cost"], 2), "count": v["count"]}
                for k, v in by_category.items()
            ),
            key=lambda x: -x["annual_cost"],
        ),
        "top_suppliers": sorted(
            (
                {"supplier": k, "annual_cost": round(v["annual_cost"], 2), "count": v["count"]}
                for k, v in by_supplier.items()
            ),
            key=lambda x: -x["annual_cost"],
        )[:5],
    }


# ---------- Export CSV (Excel) ----------

STATUS_LABELS = {"active": "Actif", "in_notice": "En préavis", "expired": "Expiré"}


def _csv_safe(value) -> str:
    """Neutralise les formules (=, +, -, @) interprétées par Excel à l'ouverture."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def _fr_number(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _fr_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def contracts_csv(contracts: list[Contract]) -> str:
    """CSV séparé par des points-virgules (Excel français), avec BOM UTF-8."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Contrat", "Fournisseur", "Catégorie", "Montant total (€)", "Coût annuel (€)",
        "Durée (mois)", "Début", "Fin", "Préavis (jours)", "Date limite de résiliation",
        "Statut", "Reconduction tacite", "Décision", "Commentaire décision", "Lien SharePoint", "Notes",
    ])
    for c in contracts:
        writer.writerow([
            _csv_safe(c.name), _csv_safe(c.supplier), c.category_label,
            _fr_number(float(c.amount)), _fr_number(c.annual_cost), c.duration_months,
            _fr_date(c.start_date), _fr_date(c.end_date), c.notice_period_days,
            _fr_date(c.termination_deadline), STATUS_LABELS.get(c.computed_status, c.computed_status),
            "Oui" if c.auto_renewal else "Non", c.decision_label, _csv_safe(c.decision_comment),
            _csv_safe(c.sharepoint_file_url), _csv_safe(c.notes),
        ])
    return "﻿" + buffer.getvalue()
