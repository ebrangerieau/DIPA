"""
Router système (administrateurs) : sauvegarde / restauration, état des connecteurs,
alertes e-mail et journal des actions.

La sauvegarde applicative est un fichier JSON validé à l'import : restaurer un script
SQL fourni par l'utilisateur reviendrait à exécuter du SQL arbitraire sur la base.
La sauvegarde complète de PostgreSQL relève du serveur (voir scripts/backup_db.sh).
"""
import json
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app import scheduler, timeutils
from app.auth import require_admin
from app.config import settings
from app.database import get_db
from app.models.contract import Contract
from app.models.contract_event import ContractEvent
from app.models.notification import NotificationLog
from app.models.user import User
from app.routers.tickets import get_zammad_service
from app.schemas.contracts import ContractFields, Decision
from app.services import alerts_service, contract_service
from app.services.mail_service import MailError, send_mail
from app.services.zammad_service import ZammadError, ZammadService

router = APIRouter(prefix="/system", tags=["système"])

BACKUP_FORMAT = "cockpit-it-backup"
BACKUP_VERSION = 1
MAX_BACKUP_BYTES = 10 * 1024 * 1024


class BackupContract(ContractFields):
    id: uuid.UUID
    renewal_decision: Decision = "pending"
    decision_comment: Optional[str] = None
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class BackupEvent(BaseModel):
    contract_id: Optional[uuid.UUID] = None
    contract_name: str = Field(max_length=255)
    event_type: str = Field(max_length=30)
    details: Optional[dict] = None
    username: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime


class BackupFile(BaseModel):
    format: Literal["cockpit-it-backup"]
    version: int
    contracts: list[BackupContract]
    events: list[BackupEvent] = Field(default_factory=list)


def _iso(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


# ---------- Sauvegarde / restauration ----------

@router.get("/backup")
def backup(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Télécharge les contrats et leur historique au format JSON."""
    contracts = []
    for c in db.query(Contract).order_by(Contract.name).all():
        data = contract_service.snapshot(c)
        data.update(
            id=str(c.id),
            decision_by=c.decision_by,
            decision_at=_iso(c.decision_at),
            created_at=_iso(c.created_at),
        )
        contracts.append(data)
    events = [
        {
            "contract_id": str(e.contract_id) if e.contract_id else None,
            "contract_name": e.contract_name,
            "event_type": e.event_type,
            "details": e.details,
            "username": e.username,
            "created_at": _iso(e.created_at),
        }
        for e in db.query(ContractEvent).order_by(ContractEvent.created_at).all()
    ]
    payload = {
        "format": BACKUP_FORMAT,
        "version": BACKUP_VERSION,
        "app_version": settings.app_version,
        "exported_at": timeutils.utcnow().isoformat() + "Z",
        "contracts": contracts,
        "events": events,
    }
    filename = f"cockpit-it_sauvegarde_{timeutils.local_now().strftime('%Y-%m-%d_%H%M')}.json"
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/restore")
async def restore(
    file: UploadFile = File(..., description="Fichier JSON produit par /system/backup"),
    mode: Literal["merge", "replace"] = Form("merge"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Restaure une sauvegarde JSON.
    - merge : ajoute les contrats absents et met à jour ceux qui existent (même identifiant) ;
    - replace : remplace l'ensemble des contrats et de leur historique.
    """
    raw = await file.read(MAX_BACKUP_BYTES + 1)
    if len(raw) > MAX_BACKUP_BYTES:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (10 Mo maximum)")
    try:
        backup_file = BackupFile.model_validate(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Le fichier n'est pas un JSON valide") from None
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(p) for p in first.get("loc", ()))
        raise HTTPException(status_code=400, detail=f"Sauvegarde invalide ({location}) : {first.get('msg')}") from exc
    if backup_file.version > BACKUP_VERSION:
        raise HTTPException(status_code=400, detail="Sauvegarde produite par une version plus récente de l'application")

    def apply() -> dict:
        created = updated = 0
        if mode == "replace":
            db.query(NotificationLog).delete()
            db.query(ContractEvent).delete()
            db.query(Contract).delete()
            db.flush()
        for item in backup_file.contracts:
            values = item.model_dump()
            if values.get("created_at") is None:
                values.pop("created_at")
            contract = db.get(Contract, item.id)
            if contract is None:
                db.add(Contract(**values))
                created += 1
            else:
                for field, value in values.items():
                    setattr(contract, field, value)
                updated += 1
        db.flush()
        imported_events = 0
        if mode == "replace":
            known_ids = {c.id for c in backup_file.contracts}
            for event in backup_file.events:
                data = event.model_dump()
                if data["contract_id"] not in known_ids:
                    data["contract_id"] = None
                db.add(ContractEvent(**data))
                imported_events += 1
        for item in backup_file.contracts:
            contract = db.get(Contract, item.id)
            contract_service.log_event(db, contract, "restored", admin.username, {"mode": mode, "fichier": file.filename})
        db.commit()
        return {"mode": mode, "created": created, "updated": updated, "events": imported_events}

    return await run_in_threadpool(apply)


# ---------- État, alertes, journal ----------

@router.get("/status")
async def system_status(
    zammad: ZammadService = Depends(get_zammad_service),
    _: User = Depends(require_admin),
):
    """État des connecteurs et de la configuration (sans aucun secret)."""
    zammad_reachable, zammad_error = False, None
    if settings.zammad_configured:
        try:
            await zammad.check_connection()
            zammad_reachable = True
        except ZammadError as exc:
            zammad_error = str(exc)
    else:
        zammad_error = "Non configuré"

    last_result = scheduler.state.get("last_result") or {}
    return {
        "version": settings.app_version,
        "zammad": {
            "configured": settings.zammad_configured,
            "reachable": zammad_reachable,
            "error": zammad_error,
            "project_tag": settings.zammad_project_tag,
        },
        "auth": {
            "local_enabled": settings.enable_local_auth,
            "sso_enabled": settings.sso_enabled,
            "sso_auto_activate": settings.sso_auto_activate,
            "cookie_secure": settings.cookie_secure_effective,
        },
        "mail": {
            "backend": settings.mail_backend,
            "configured": settings.mail_configured,
            "sender": settings.mail_from or None,
            "recipients": settings.alert_recipients,
        },
        "alerts": {
            "enabled": settings.alerts_enabled,
            "scheduler_enabled": settings.scheduler_enabled,
            "hour": settings.alert_hour,
            "deadline_thresholds": sorted(settings.alert_days_before_deadline, reverse=True),
            "end_days": settings.alert_end_days,
            "last_run": scheduler.state.get("last_run"),
            "last_error": scheduler.state.get("last_error"),
            "last_sent": last_result.get("sent"),
            "last_skipped_reason": last_result.get("skipped_reason"),
        },
    }


@router.get("/alerts/preview")
def alerts_preview(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Aperçu des alertes qui seraient envoyées aujourd'hui (rien n'est envoyé ni modifié)."""
    return alerts_service.run_alerts(db, dry_run=True)


@router.post("/alerts/run")
def alerts_run(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Exécute immédiatement la tâche quotidienne (reconductions + récapitulatif)."""
    try:
        result = alerts_service.run_alerts(db)
    except MailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    scheduler.state.update(last_run=timeutils.utcnow().isoformat(), last_result=result, last_error=None)
    return result


@router.post("/alerts/test")
def alerts_test(admin: User = Depends(require_admin)):
    """Envoie un e-mail de test aux destinataires des alertes (ou à l'administrateur)."""
    recipients = settings.alert_recipients or [admin.email]
    try:
        send_mail(
            f"[{settings.app_name}] E-mail de test",
            "<p>L'envoi des alertes du Cockpit IT fonctionne.</p>",
            recipients,
        )
    except MailError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"sent_to": recipients}


@router.get("/events")
def recent_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Journal des dernières actions sur les contrats (tous contrats confondus)."""
    events = (
        db.query(ContractEvent)
        .order_by(ContractEvent.created_at.desc(), ContractEvent.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "contract_id": str(e.contract_id) if e.contract_id else None,
            "contract_name": e.contract_name,
            "event_type": e.event_type,
            "event_label": e.event_label,
            "details": e.details,
            "username": e.username,
            "created_at": _iso(e.created_at),
        }
        for e in events
    ]
