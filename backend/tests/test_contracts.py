"""
Tests des contrats : droits, validation, règles de préavis (CDC §4.1), timeline,
décisions, renouvellement, historique et export.
Date du jour figée au 22/09/2026 (voir conftest).
"""
from datetime import date

import pytest

from app.models.contract import COLOR_ACTIVE, COLOR_EXPIRED, COLOR_NOTICE, COLOR_URGENT, Contract
from app.services import contract_service
from tests.conftest import contract_payload


def _create(client, **overrides):
    response = client.post("/api/contracts", json=contract_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------- Droits ----------

def test_reader_can_read_but_not_write(admin_client, reader_user, client):
    created = _create(admin_client)
    admin_client.post("/api/auth/logout")
    from tests.conftest import READER_PASSWORD, login
    login(client, "lecteur", READER_PASSWORD)
    client.headers.update({"X-Requested-With": "XMLHttpRequest"})

    assert client.get("/api/contracts").status_code == 200
    assert client.get(f"/api/contracts/{created['id']}").status_code == 200
    assert client.post("/api/contracts", json=contract_payload()).status_code == 403
    assert client.put(f"/api/contracts/{created['id']}", json={"name": "X"}).status_code == 403
    assert client.delete(f"/api/contracts/{created['id']}").status_code == 403
    assert client.post(f"/api/contracts/{created['id']}/decision", json={"decision": "renew"}).status_code == 403


# ---------- CRUD et validation ----------

def test_create_and_read_contract(admin_client):
    created = _create(admin_client)
    assert created["name"] == "Licence antivirus"
    assert created["annual_cost"] == pytest.approx(1200.0)
    assert created["category_label"] == "Licences logicielles"
    assert created["renewal_decision"] == "pending"
    fetched = admin_client.get(f"/api/contracts/{created['id']}").json()
    assert fetched["termination_deadline"] == "2026-10-02"


def test_create_contract_invalid_dates(admin_client):
    response = admin_client.post("/api/contracts", json=contract_payload(end_date="2023-12-31"))
    assert response.status_code == 422
    assert "date de fin doit être postérieure" in response.json()["detail"]


def test_missing_field_message_is_french(admin_client):
    payload = contract_payload()
    del payload["supplier"]
    response = admin_client.post("/api/contracts", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Fournisseur : champ obligatoire"


def test_javascript_link_is_rejected(admin_client):
    response = admin_client.post("/api/contracts", json=contract_payload(sharepoint_file_url="javascript:alert(1)"))
    assert response.status_code == 422


def test_partial_update_is_validated_as_a_whole(admin_client):
    created = _create(admin_client)
    response = admin_client.put(f"/api/contracts/{created['id']}", json={"end_date": "2023-01-01"})
    assert response.status_code == 422
    response = admin_client.put(f"/api/contracts/{created['id']}", json={"amount": 4200, "sharepoint_file_url": ""})
    assert response.status_code == 200
    assert response.json()["amount"] == 4200
    assert response.json()["sharepoint_file_url"] is None


def test_unknown_contract_returns_404(admin_client):
    assert admin_client.get("/api/contracts/00000000-0000-0000-0000-000000000000").status_code == 404


# ---------- Règles de préavis (CDC §4.1) ----------

@pytest.mark.parametrize("end_date, notice, status, color, item_type", [
    ("2026-12-31", 90, "active", COLOR_ACTIVE, "contract-milestone"),    # préavis au 02/10
    ("2026-11-30", 90, "in_notice", COLOR_NOTICE, "contract-notice"),    # 69 j avant l'échéance
    ("2026-10-10", 60, "in_notice", COLOR_URGENT, "contract-notice"),    # 18 j avant l'échéance
    ("2026-09-01", 30, "expired", COLOR_EXPIRED, "contract-milestone"),
])
def test_status_color_and_timeline_rules(admin_client, end_date, notice, status, color, item_type):
    created = _create(admin_client, start_date="2025-09-01", end_date=end_date, notice_period_days=notice)
    assert created["computed_status"] == status
    assert created["timeline_color"] == color
    items = admin_client.get("/api/contracts/timeline/data").json()
    assert len(items) == 1
    assert items[0]["type"] == item_type
    assert items[0]["color"] == color
    assert items[0]["group"] == "contracts"
    assert items[0]["metadata"]["sharepoint_url"].startswith("https://")
    if item_type == "contract-notice":
        assert items[0]["end"] == end_date
    else:
        assert items[0]["start"] == end_date and items[0]["end"] is None


def test_filters(admin_client):
    _create(admin_client, name="Actif", supplier="Alpha")
    _create(admin_client, name="Préavis", supplier="Beta", start_date="2025-09-01", end_date="2026-11-30", category="telecom")
    _create(admin_client, name="Expiré", supplier="Alpha", start_date="2025-01-01", end_date="2026-06-30")

    def names(params):
        return [c["name"] for c in admin_client.get("/api/contracts", params=params).json()]

    assert names({"status": "in_notice"}) == ["Préavis"]
    assert sorted(names({"supplier": "alpha"})) == ["Actif", "Expiré"]
    assert names({"category": "telecom"}) == ["Préavis"]
    assert names({"q": "expi"}) == ["Expiré"]
    assert admin_client.get("/api/contracts/suppliers").json() == ["Alpha", "Beta"]
    assert admin_client.get("/api/contracts", params={"status": "inconnu"}).status_code == 422


# ---------- Décision, renouvellement, historique ----------

def test_decision_and_history(admin_client):
    created = _create(admin_client)
    response = admin_client.post(f"/api/contracts/{created['id']}/decision",
                                 json={"decision": "terminate", "comment": "Remplacé par la solution X"})
    assert response.status_code == 200
    data = response.json()
    assert data["decision_label"] == "À résilier"
    assert data["decision_by"] == "Admin"

    events = admin_client.get(f"/api/contracts/{created['id']}/events").json()
    assert [e["event_type"] for e in events] == ["decision", "created"]
    assert events[0]["username"] == "admin"

    # Renouveler un contrat dont la résiliation est décidée est refusé
    assert admin_client.post(f"/api/contracts/{created['id']}/renew", json={}).status_code == 400


def test_renew_rolls_period_forward(admin_client):
    created = _create(admin_client)  # 01/01/2024 -> 31/12/2026, 36 mois
    admin_client.post(f"/api/contracts/{created['id']}/decision", json={"decision": "renew"})
    response = admin_client.post(f"/api/contracts/{created['id']}/renew", json={"amount": 3900, "duration_months": 12})
    assert response.status_code == 200
    data = response.json()
    assert data["start_date"] == "2027-01-01"
    assert data["end_date"] == "2027-12-31"
    assert data["amount"] == 3900
    assert data["renewal_decision"] == "pending"
    events = admin_client.get(f"/api/contracts/{created['id']}/events").json()
    assert events[0]["event_type"] == "renewed"
    assert events[0]["details"]["avant"]["end_date"] == "2026-12-31"


def test_update_is_traced_with_changes(admin_client):
    created = _create(admin_client)
    admin_client.put(f"/api/contracts/{created['id']}", json={"amount": 4000})
    event = admin_client.get(f"/api/contracts/{created['id']}/events").json()[0]
    assert event["event_type"] == "updated"
    assert event["details"]["changes"] == {"amount": [3600.0, 4000.0]}


def test_delete_keeps_audit_trail(admin_client):
    created = _create(admin_client)
    assert admin_client.delete(f"/api/contracts/{created['id']}").status_code == 204
    assert admin_client.get(f"/api/contracts/{created['id']}").status_code == 404
    journal = admin_client.get("/api/system/events").json()
    assert journal[0]["event_type"] == "deleted"
    assert journal[0]["contract_name"] == "Licence antivirus"
    assert journal[0]["contract_id"] is None


def test_auto_renewal_process(db_session):
    tacit = Contract(name="Tacite", supplier="S", amount=1200, duration_months=12, start_date=date(2025, 9, 1),
                     end_date=date(2026, 8, 31), notice_period_days=60, auto_renewal=True)
    terminated = Contract(name="Résilié", supplier="S", amount=1200, duration_months=12, start_date=date(2025, 9, 1),
                          end_date=date(2026, 8, 31), notice_period_days=60, auto_renewal=True,
                          renewal_decision="terminate")
    late = Contract(name="Rattrapage", supplier="S", amount=100, duration_months=12, start_date=date(2023, 1, 1),
                    end_date=date(2023, 12, 31), notice_period_days=30, auto_renewal=True)
    db_session.add_all([tacit, terminated, late])
    db_session.commit()

    renewed = contract_service.process_auto_renewals(db_session, date(2026, 9, 22))
    assert {r["name"] for r in renewed} == {"Tacite", "Rattrapage"}
    assert (tacit.start_date, tacit.end_date) == (date(2026, 9, 1), date(2027, 8, 31))
    assert late.end_date == date(2026, 12, 31)  # Trois périodes rattrapées
    assert terminated.end_date == date(2026, 8, 31)
    assert contract_service.process_auto_renewals(db_session, date(2026, 9, 22)) == []


def test_upcoming_actions_and_kpis(db_session):
    db_session.add_all([
        Contract(name="Loin", supplier="A", amount=1000, duration_months=12, start_date=date(2026, 6, 1),
                 end_date=date(2027, 5, 31), notice_period_days=60),
        Contract(name="Bientôt", supplier="B", amount=2400, duration_months=24, start_date=date(2025, 1, 1),
                 end_date=date(2026, 12, 31), notice_period_days=90, auto_renewal=True, category="telecom"),
        Contract(name="Préavis", supplier="B", amount=600, duration_months=12, start_date=date(2025, 11, 1),
                 end_date=date(2026, 10, 31), notice_period_days=60),
        Contract(name="Expiré", supplier="C", amount=999, duration_months=12, start_date=date(2025, 1, 1),
                 end_date=date(2025, 12, 31), notice_period_days=30),
    ])
    db_session.commit()
    contracts = db_session.query(Contract).all()

    actions = contract_service.upcoming_actions(contracts, 90)
    assert [a["name"] for a in actions] == ["Bientôt", "Préavis"]
    assert actions[0]["key_date"] == "2026-10-02" and actions[0]["urgency"] == "high"
    assert "reconduction tacite" in actions[0]["message"]
    assert actions[1]["key_date"] == "2026-10-31"

    kpis = contract_service.contract_kpis(contracts, 90)
    assert (kpis["total"], kpis["active"], kpis["in_notice"], kpis["expired"]) == (4, 2, 1, 1)
    assert kpis["annual_budget"] == pytest.approx(1000 + 1200 + 600)
    assert kpis["pending_decisions"] == 2
    assert kpis["top_suppliers"][0] == {"supplier": "B", "annual_cost": 1800.0, "count": 2}


# ---------- Export ----------

def test_csv_export(admin_client):
    _create(admin_client, name="=HYPERLINK(\"http://pirate\")", notes="+cmd")
    response = admin_client.get("/api/contracts/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    text = response.content.decode("utf-8")
    assert text.startswith("﻿Contrat;Fournisseur")
    assert "'=HYPERLINK" in text  # Formule neutralisée
    assert "'+cmd" in text
    assert "1200,00" in text and "02/10/2026" in text
