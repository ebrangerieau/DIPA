"""
Tests de la gestion des utilisateurs et des fonctions système (sauvegarde / restauration).
"""
import json

from app.main import app
from app.routers.tickets import get_zammad_service
from tests.conftest import contract_payload, login
from tests.zammad_fake import FakeZammad


# ---------- Utilisateurs ----------

def test_admin_creates_user_with_forced_password_change(admin_client):
    response = admin_client.post("/api/users", json={
        "username": "technicien", "email": "Tech@Exemple.test", "full_name": "Technicien",
        "password": "Temporaire-2026!", "is_admin": False,
    })
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["must_change_password"] is True
    assert data["email"] == "tech@exemple.test"
    assert len(admin_client.get("/api/users").json()) == 2


def test_user_creation_enforces_password_policy(admin_client):
    response = admin_client.post("/api/users", json={
        "username": "technicien", "email": "tech@exemple.test", "password": "trop-court",
    })
    assert response.status_code == 400


def test_reader_cannot_manage_users(reader_client):
    assert reader_client.get("/api/users").status_code == 403


def test_last_admin_is_protected(admin_client, admin_user, reader_user):
    response = admin_client.patch(f"/api/users/{admin_user.id}", json={"is_admin": False})
    assert response.status_code == 400
    assert admin_client.delete(f"/api/users/{admin_user.id}").status_code == 400


def test_deactivation_closes_sessions(client, admin_user, reader_user):
    login(client, "lecteur", "Mot-de-passe-lecteur-2026")
    reader_cookie = client.cookies.get("cockpit_session")
    login(client, "admin", "Mot-de-passe-admin-2026")
    client.headers.update({"X-Requested-With": "XMLHttpRequest"})
    assert client.patch(f"/api/users/{reader_user.id}", json={"is_active": False}).status_code == 200

    client.cookies.clear()
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {reader_cookie}"})
    assert response.status_code == 401


def test_sso_account_validation_by_admin(admin_client, db_session):
    from app.models.user import User

    pending = User(username="prof@ecole.test", email="prof@ecole.test", auth_provider="entra",
                   entra_oid="oid-9", is_active=False)
    db_session.add(pending)
    db_session.commit()
    response = admin_client.patch(f"/api/users/{pending.id}", json={"is_active": True})
    assert response.json()["is_active"] is True


# ---------- Sauvegarde / restauration ----------

def test_backup_and_replace_restore_roundtrip(admin_client):
    first = admin_client.post("/api/contracts", json=contract_payload(name="Contrat A")).json()
    admin_client.post("/api/contracts", json=contract_payload(name="Contrat B"))
    backup = admin_client.get("/api/system/backup")
    assert backup.status_code == 200
    assert "attachment" in backup.headers["content-disposition"]
    data = backup.json()
    assert data["format"] == "cockpit-it-backup" and len(data["contracts"]) == 2

    admin_client.delete(f"/api/contracts/{first['id']}")
    admin_client.post("/api/contracts", json=contract_payload(name="Contrat C"))

    response = admin_client.post(
        "/api/system/restore",
        files={"file": ("sauvegarde.json", json.dumps(data), "application/json")},
        data={"mode": "replace"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 2
    names = sorted(c["name"] for c in admin_client.get("/api/contracts").json())
    assert names == ["Contrat A", "Contrat B"]
    restored = admin_client.get(f"/api/contracts/{first['id']}/events").json()
    assert restored[0]["event_type"] == "restored"


def test_merge_restore_updates_existing(admin_client):
    created = admin_client.post("/api/contracts", json=contract_payload(name="Avant")).json()
    data = admin_client.get("/api/system/backup").json()
    data["contracts"][0]["name"] = "Après"
    response = admin_client.post(
        "/api/system/restore",
        files={"file": ("s.json", json.dumps(data), "application/json")},
        data={"mode": "merge"},
    )
    assert response.json()["updated"] == 1
    assert admin_client.get(f"/api/contracts/{created['id']}").json()["name"] == "Après"


def test_restore_rejects_invalid_files(admin_client):
    bad_json = admin_client.post("/api/system/restore", files={"file": ("x.json", "pas du json", "application/json")})
    assert bad_json.status_code == 400
    wrong_format = admin_client.post(
        "/api/system/restore",
        files={"file": ("x.json", json.dumps({"format": "autre", "version": 1, "contracts": []}), "application/json")},
    )
    assert wrong_format.status_code == 400
    sql_dump = admin_client.post("/api/system/restore", files={"file": ("x.sql", "DROP TABLE users;", "text/plain")})
    assert sql_dump.status_code == 400


def test_reader_cannot_backup(reader_client):
    assert reader_client.get("/api/system/backup").status_code == 403


def test_system_status_hides_secrets(admin_client):
    fake = FakeZammad(lambda q: [])
    app.dependency_overrides[get_zammad_service] = fake.service
    try:
        data = admin_client.get("/api/system/status").json()
    finally:
        del app.dependency_overrides[get_zammad_service]
    assert data["zammad"]["reachable"] is True
    assert "token-de-test" not in json.dumps(data)
