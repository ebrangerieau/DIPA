"""
Alertes e-mail sur les échéances de contrats (CDC Phase 2 : « notifications avant échéance »).

Chaque jour, un récapitulatif est envoyé s'il y a du nouveau :
- date limite de résiliation dans N jours (paliers ALERT_DAYS_BEFORE_DEADLINE, ex. 60/30/7) ;
- fin prochaine d'un contrat sans reconduction tacite (ou dont la résiliation est décidée) ;
- reconductions tacites effectuées automatiquement.
Le journal `notification_log` garantit qu'une alerte n'est envoyée qu'une fois.
"""
import html
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app import timeutils
from app.config import settings
from app.models.contract import Contract
from app.models.notification import NotificationLog
from app.services import contract_service
from app.services.mail_service import send_mail

logger = logging.getLogger(__name__)


@dataclass
class DueAlert:
    contract: Contract
    kind: str
    reference_date: date
    days: int
    message: str

    def as_dict(self) -> dict:
        return {
            "contract_id": str(self.contract.id),
            "name": self.contract.name,
            "supplier": self.contract.supplier,
            "kind": self.kind,
            "reference_date": self.reference_date.isoformat(),
            "days": self.days,
            "message": self.message,
            "decision_label": self.contract.decision_label,
        }


def compute_due_alerts(db: Session, today: Optional[date] = None) -> list[DueAlert]:
    """Alertes à envoyer aujourd'hui (non encore envoyées)."""
    today = today or timeutils.today()
    thresholds = sorted(set(d for d in settings.alert_days_before_deadline if d >= 0))
    already_sent = {
        (n.contract_id, n.kind, n.reference_date)
        for n in db.query(NotificationLog).filter(NotificationLog.reference_date >= today).all()
    }
    due = []
    for c in db.query(Contract).order_by(Contract.end_date).all():
        if c.is_expired:
            continue

        # 1. Approche de la date limite de résiliation (palier le plus proche atteint)
        days = (c.termination_deadline - today).days
        nothing_to_do = c.auto_renewal and c.renewal_decision == "renew"
        tier = next((t for t in thresholds if 0 <= days <= t), None)
        if tier is not None and not nothing_to_do:
            kind = f"deadline_{tier}"
            if (c.id, kind, c.termination_deadline) not in already_sent:
                label = "aujourd'hui" if days == 0 else f"dans {days} jour{'s' if days > 1 else ''}"
                due.append(DueAlert(c, kind, c.termination_deadline, days,
                                    f"Date limite de résiliation {label}"))

        # 2. Fin de contrat prochaine (sans reconduction tacite ou résiliation décidée)
        end_days = (c.end_date - today).days
        if 0 <= end_days <= settings.alert_end_days and (not c.auto_renewal or c.renewal_decision == "terminate"):
            if (c.id, "end", c.end_date) not in already_sent:
                due.append(DueAlert(c, "end", c.end_date, end_days,
                                    f"Fin du contrat dans {end_days} jour{'s' if end_days > 1 else ''}"))
    return due


def _fmt_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def build_digest(alerts: list[DueAlert], renewals: list[dict], today: date) -> tuple[str, str]:
    """Construit le sujet et le corps HTML du récapitulatif."""
    subject = f"[{settings.app_name}] {len(alerts)} échéance(s) de contrat à suivre"
    if not alerts:
        subject = f"[{settings.app_name}] Reconduction(s) tacite(s) effectuée(s)"

    rows = "".join(
        "<tr>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb'><strong>{html.escape(a.contract.name)}</strong><br>"
        f"<span style='color:#6b7280'>{html.escape(a.contract.supplier)}</span></td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb'>{html.escape(a.message)}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb'>{_fmt_date(a.reference_date)}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #e5e7eb'>{html.escape(a.contract.decision_label)}</td>"
        "</tr>"
        for a in alerts
    )
    renewal_items = "".join(
        f"<li>{html.escape(r['name'])} : nouvelle échéance le "
        f"{_fmt_date(date.fromisoformat(r['apres']['end_date']))}</li>"
        for r in renewals
    )
    link = ""
    if settings.app_public_url:
        url = html.escape(settings.app_public_url.rstrip("/") + "/contrats")
        link = f"<p><a href='{url}'>Ouvrir le Cockpit IT</a></p>"

    body = [
        "<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#111827'>",
        f"<h2 style='margin:0 0 12px'>{html.escape(settings.app_name)} – suivi des contrats</h2>",
        f"<p>Récapitulatif du {_fmt_date(today)}.</p>",
    ]
    if alerts:
        body.append(
            "<table style='border-collapse:collapse;width:100%'>"
            "<thead><tr style='background:#f3f4f6;text-align:left'>"
            "<th style='padding:6px 10px'>Contrat</th><th style='padding:6px 10px'>Alerte</th>"
            "<th style='padding:6px 10px'>Date</th><th style='padding:6px 10px'>Décision</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
        )
    if renewals:
        body.append(f"<h3>Reconductions tacites effectuées</h3><ul>{renewal_items}</ul>")
    body.append(link)
    body.append("<p style='color:#6b7280;font-size:12px'>Message automatique, merci de ne pas répondre.</p></div>")
    return subject, "".join(body)


def run_alerts(db: Session, *, dry_run: bool = False, today: Optional[date] = None) -> dict:
    """
    Tâche quotidienne : reconductions tacites puis envoi du récapitulatif.
    En mode `dry_run`, rien n'est modifié ni envoyé (aperçu).
    """
    today = today or timeutils.today()
    renewals = [] if dry_run else contract_service.process_auto_renewals(db, today)
    due = compute_due_alerts(db, today)
    result = {
        "date": today.isoformat(),
        "alerts": [a.as_dict() for a in due],
        "renewals": renewals,
        "sent": False,
        "skipped_reason": None,
    }
    if dry_run:
        return result
    if not due and not renewals:
        result["skipped_reason"] = "Aucune nouvelle alerte"
        return result
    if not settings.alerts_enabled:
        result["skipped_reason"] = "Alertes désactivées (ALERTS_ENABLED=false)"
        return result
    if not settings.alert_recipients:
        result["skipped_reason"] = "Aucun destinataire (ALERT_RECIPIENTS)"
        return result

    subject, body = build_digest(due, renewals, today)
    send_mail(subject, body, settings.alert_recipients)  # MailError propagée : nouvel essai plus tard
    for alert in due:
        db.add(NotificationLog(contract_id=alert.contract.id, kind=alert.kind, reference_date=alert.reference_date))
    db.commit()
    result["sent"] = True
    logger.info("Récapitulatif envoyé : %s alerte(s), %s reconduction(s)", len(due), len(renewals))
    return result
