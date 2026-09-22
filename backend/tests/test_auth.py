"""
Tests d'authentification et de sécurité des sessions.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.user import User
from app.services import user_service
from tests.conftest import ADMIN_PASSWORD, READER_PASSWORD, login


@pytest.mark.parametrize("path", [
    "/api/contracts",
    "/api/contracts/timeline/data",
    "/api/tickets/stats",
    "/api/tickets/timeline/data",
    "/api/dashboard/summary",
    "/api/system/backup",
    "/api/users",
    "/api/auth/me",
])
def test_endpoints_require_authentication(client, path):
    assert client.get(path).status_code == 401


def test_public_registration_is_removed(client):
    response = client.post("/api/auth/register", json={"username": "x", "email": "x@x.fr", "password": "x" * 12})
    assert response.status_code in (404, 405)


def test_auth_config_is_public(client):
    data = client.get("/api/auth/config").json()
    assert data["local_enabled"] is True
    assert data["sso_enabled"] is False


def test_login_sets_httponly_cookie(client, admin_user):
    response = login(client, "admin", ADMIN_PASSWORD)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "path=/api" in cookie
    assert "samesite=lax" in cookie
    assert response.json()["user"]["username"] == "admin"
    assert client.get("/api/auth/me").json()["is_admin"] is True


def test_login_accepts_email_case_insensitive(client, admin_user):
    login(client, "ADMIN@exemple.test", ADMIN_PASSWORD)


def test_login_with_wrong_password_is_rejected(client, admin_user):
    response = client.post("/api/auth/login/local", data={"username": "admin", "password": "mauvais-mot-de-passe"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Identifiants incorrects"


def test_login_is_rate_limited(client, admin_user):
    for _ in range(settings.login_max_attempts):
        client.post("/api/auth/login/local", data={"username": "admin", "password": "mauvais-mot-de-passe"})
    response = client.post("/api/auth/login/local", data={"username": "admin", "password": ADMIN_PASSWORD})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_inactive_account_cannot_login(client, db_session, reader_user):
    reader_user.is_active = False
    db_session.commit()
    response = client.post("/api/auth/login/local", data={"username": "lecteur", "password": READER_PASSWORD})
    assert response.status_code == 403


def test_logout_closes_session(admin_client):
    assert admin_client.post("/api/auth/logout").status_code == 204
    assert admin_client.get("/api/auth/me").status_code == 401


def test_cookie_mutations_require_csrf_header(client, admin_user):
    login(client, "admin", ADMIN_PASSWORD)
    payload = {
        "name": "Test", "supplier": "Fournisseur", "amount": 100, "duration_months": 12,
        "start_date": "2026-01-01", "end_date": "2026-12-31", "notice_period_days": 30,
    }
    assert client.post("/api/contracts", json=payload).status_code == 403
    response = client.post("/api/contracts", json=payload, headers={"X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 201


def test_bearer_token_for_api_clients(client, admin_user):
    token = login(client, "admin", ADMIN_PASSWORD).json()["access_token"]
    with TestClient(app) as other:  # Sans cookie : jeton dans l'en-tête, pas de CSRF possible
        response = other.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200


def test_tampered_token_is_rejected(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code == 401


def test_weak_password_forces_change(client, db_session):
    user = User(username="faible", email="faible@exemple.test", hashed_password=User.hash_password("Court-123"), is_active=True)
    db_session.add(user)
    db_session.commit()
    data = login(client, "faible", "Court-123").json()
    assert data["user"]["must_change_password"] is True


def test_published_password_is_blocked(client, db_session):
    # « admin123 » : ancien mot de passe par défaut documenté dans l'historique du dépôt
    user = User(username="ancien", email="ancien@exemple.test", hashed_password=User.hash_password("admin123"), is_active=True)
    db_session.add(user)
    db_session.commit()
    response = client.post("/api/auth/login/local", data={"username": "ancien", "password": "admin123"})
    assert response.status_code == 403
    assert "publié" in response.json()["detail"]


def test_bootstrap_refuses_published_password(monkeypatch, db_session):
    from app import main
    from app.config import settings

    monkeypatch.setattr(settings, "bootstrap_admin_username", "admin")
    monkeypatch.setattr(settings, "bootstrap_admin_email", "admin@exemple.test")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "admin123")
    monkeypatch.setattr(main, "SessionLocal", lambda: db_session)
    main.bootstrap_admin()
    assert db_session.query(User).count() == 0


def test_change_password_revokes_other_sessions(client, admin_user):
    old_token = login(client, "admin", ADMIN_PASSWORD).json()["access_token"]
    response = client.post(
        "/api/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "Nouveau-mot-de-passe-2026"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 204
    # La session courante reste ouverte (nouveau cookie), l'ancien jeton est révoqué
    assert client.get("/api/auth/me").status_code == 200
    with TestClient(app) as other:
        assert other.get("/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    login(client, "admin", "Nouveau-mot-de-passe-2026")


def test_change_password_enforces_policy(admin_client):
    response = admin_client.post(
        "/api/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "court"},
    )
    assert response.status_code == 400
    assert "12 caractères" in response.json()["detail"]


def test_sso_login_unavailable_when_not_configured(client):
    response = client.get("/api/auth/login", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login?error=sso_indisponible"


def test_sso_callback_without_flow_cookie(client):
    response = client.get("/api/auth/callback?code=x&state=y", follow_redirects=False)
    assert response.status_code == 302
    assert "error=session_expiree" in response.headers["location"]


# ---------- Provisionnement des comptes Microsoft ----------

def _claims(**overrides):
    claims = {"oid": "oid-1", "tid": "", "preferred_username": "Prof.Exemple@ecole.test", "name": "Prof Exemple"}
    claims.update(overrides)
    return claims


def test_new_sso_user_waits_for_admin_validation(db_session, monkeypatch):
    monkeypatch.setattr(settings, "sso_auto_activate", False)
    user = user_service.provision_sso_user(db_session, _claims())
    assert user.email == "prof.exemple@ecole.test"
    assert user.is_active is False
    assert user.is_admin is False
    assert user.auth_provider == "entra"


def test_sso_admin_email_is_activated_as_admin(db_session, monkeypatch):
    monkeypatch.setattr(settings, "sso_admin_emails", ["prof.exemple@ecole.test"])
    user = user_service.provision_sso_user(db_session, _claims())
    assert user.is_active and user.is_admin


def test_sso_rejects_other_tenant(db_session, monkeypatch):
    monkeypatch.setattr(settings, "azure_tenant_id", "tenant-attendu")
    with pytest.raises(user_service.AccessDenied):
        user_service.provision_sso_user(db_session, _claims(tid="autre-tenant"))


def test_sso_allowed_roles(db_session, monkeypatch):
    monkeypatch.setattr(settings, "sso_allowed_roles", ["Cockpit.Lecteur"])
    with pytest.raises(user_service.AccessDenied):
        user_service.provision_sso_user(db_session, _claims())
    user = user_service.provision_sso_user(db_session, _claims(roles=["Cockpit.Lecteur"]))
    assert user.entra_oid == "oid-1"


def test_sso_links_existing_account_by_email(db_session, reader_user):
    user = user_service.provision_sso_user(db_session, _claims(preferred_username="lecteur@exemple.test"))
    assert user.id == reader_user.id
    assert user.entra_oid == "oid-1"
