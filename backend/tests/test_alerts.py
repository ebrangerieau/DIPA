"""
Tests des alertes e-mail sur les échéances (date du jour figée au 22/09/2026).
"""
from datetime import date

import pytest

from app.models.contract import Contract
from app.models.notification import NotificationLog
from app.services import alerts_service
from app.services.mail_service import MailError


@pytest.fixture
def sent_mails(monkeypatch):
    mails = []
    monkeypatch.setattr(alerts_service, "send_mail", lambda subject, body, to: mails.append((subject, body, to)))
    return mails


def _contract(db, **values):
    data = dict(name="Contrat", supplier="Fournisseur", amount=1000, duration_months=12,
                start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), notice_period_days=90)
    data.update(values)
    contract = Contract(**data)
    db.add(contract)
    db.commit()
    return contract


def test_deadline_tiers(db_session):
    _contract(db_session, name="J-10")                                   # limite au 02/10
    _contract(db_session, name="J-40", end_date=date(2027, 1, 31))       # limite au 02/11
    _contract(db_session, name="J-100", end_date=date(2027, 3, 31))      # hors paliers
    alerts = {a.contract.name: a for a in alerts_service.compute_due_alerts(db_session, date(2026, 9, 22))}
    assert set(alerts) == {"J-10", "J-40"}
    assert alerts["J-10"].kind == "deadline_30" and alerts["J-10"].days == 10
    assert alerts["J-40"].kind == "deadline_60"
    assert "dans 10 jours" in alerts["J-10"].message


def test_no_alert_when_tacit_renewal_is_decided(db_session):
    _contract(db_session, auto_renewal=True, renewal_decision="renew")
    assert alerts_service.compute_due_alerts(db_session, date(2026, 9, 22)) == []


def test_end_alert_for_contract_without_tacit_renewal(db_session):
    _contract(db_session, name="Fin proche", start_date=date(2025, 10, 1), end_date=date(2026, 9, 30), notice_period_days=30)
    kinds = [a.kind for a in alerts_service.compute_due_alerts(db_session, date(2026, 9, 22))]
    assert kinds == ["end"]


def test_run_sends_digest_once(db_session, sent_mails):
    _contract(db_session, name="Antivirus <script>")
    result = alerts_service.run_alerts(db_session, today=date(2026, 9, 22))
    assert result["sent"] is True
    subject, body, recipients = sent_mails[0]
    assert "1 échéance" in subject
    assert recipients == ["equipe-it@exemple.test"]
    assert "Antivirus &lt;script&gt;" in body  # Contenu échappé
    assert db_session.query(NotificationLog).count() == 1

    second = alerts_service.run_alerts(db_session, today=date(2026, 9, 22))
    assert second["sent"] is False and second["skipped_reason"] == "Aucune nouvelle alerte"
    assert len(sent_mails) == 1


def test_next_tier_triggers_new_alert(db_session, sent_mails):
    _contract(db_session)
    alerts_service.run_alerts(db_session, today=date(2026, 9, 22))   # palier 30 j
    result = alerts_service.run_alerts(db_session, today=date(2026, 9, 26))  # 6 j : palier 7 j
    assert [a["kind"] for a in result["alerts"]] == ["deadline_7"]
    assert len(sent_mails) == 2


def test_dry_run_changes_nothing(db_session, sent_mails):
    contract = _contract(db_session, auto_renewal=True, end_date=date(2026, 8, 31), start_date=date(2025, 9, 1))
    result = alerts_service.run_alerts(db_session, dry_run=True, today=date(2026, 9, 22))
    assert result["sent"] is False and result["renewals"] == []
    assert contract.end_date == date(2026, 8, 31)
    assert sent_mails == []


def test_mail_failure_keeps_alert_pending(db_session, monkeypatch):
    def failing(*args):
        raise MailError("SMTP indisponible")

    monkeypatch.setattr(alerts_service, "send_mail", failing)
    _contract(db_session)
    with pytest.raises(MailError):
        alerts_service.run_alerts(db_session, today=date(2026, 9, 22))
    assert db_session.query(NotificationLog).count() == 0  # Nouvel essai à la prochaine exécution


def test_admin_alert_endpoints(admin_client, sent_mails):
    preview = admin_client.get("/api/system/alerts/preview").json()
    assert preview["sent"] is False
    response = admin_client.post("/api/system/alerts/test")
    assert response.status_code == 502  # MAIL_BACKEND=none dans les tests
