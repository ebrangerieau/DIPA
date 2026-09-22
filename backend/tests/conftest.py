"""
Configuration commune des tests : base SQLite en mémoire, Zammad simulé,
variables d'environnement neutres (aucun secret réel n'est lu).
"""
import os

# Doit précéder tout import de l'application : prioritaire sur un éventuel fichier .env
os.environ.update({
    "COCKPIT_ENV_FILE": "",  # Ne jamais lire le .env réel pendant les tests
    "DEBUG": "true",
    "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789abcdef",
    "DATABASE_URL": "sqlite://",
    "ZAMMAD_API_URL": "https://zammad.test",
    "ZAMMAD_API_TOKEN": "token-de-test",
    "ZAMMAD_PUBLIC_URL": "https://support.test",
    "ZAMMAD_PROJECT_TAG": "#Projet",
    "AZURE_TENANT_ID": "",
    "AZURE_CLIENT_ID": "",
    "AZURE_CLIENT_SECRET": "",
    "ENABLE_LOCAL_AUTH": "true",
    "BOOTSTRAP_ADMIN_USERNAME": "",
    "BOOTSTRAP_ADMIN_EMAIL": "",
    "BOOTSTRAP_ADMIN_PASSWORD": "",
    "SCHEDULER_ENABLED": "false",
    "ALERTS_ENABLED": "true",
    "ALERT_RECIPIENTS": "equipe-it@exemple.test",
    "MAIL_BACKEND": "none",
    "TIMEZONE": "Europe/Paris",
})

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import timeutils  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.routers.auth import login_limiter  # noqa: E402
from app.services import zammad_service  # noqa: E402

ADMIN_PASSWORD = "Mot-de-passe-admin-2026"
READER_PASSWORD = "Mot-de-passe-lecteur-2026"
FIXED_TODAY = date(2026, 9, 22)

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    """Date du jour figée pour des tests déterministes."""
    monkeypatch.setattr(timeutils, "today", lambda: FIXED_TODAY)
    return FIXED_TODAY


@pytest.fixture(autouse=True)
def _reset_state():
    login_limiter.clear()
    zammad_service.clear_cache()
    yield
    zammad_service.clear_cache()


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db, username, password, is_admin):
    user = User(
        username=username,
        email=f"{username}@exemple.test",
        hashed_password=User.hash_password(password),
        full_name=username.capitalize(),
        is_admin=is_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    return _create_user(db_session, "admin", ADMIN_PASSWORD, True)


@pytest.fixture
def reader_user(db_session):
    return _create_user(db_session, "lecteur", READER_PASSWORD, False)


def login(client, username, password):
    response = client.post("/api/auth/login/local", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response


@pytest.fixture
def admin_client(client, admin_user):
    """Client connecté en administrateur (cookie de session + en-tête anti-CSRF)."""
    login(client, "admin", ADMIN_PASSWORD)
    client.headers.update({"X-Requested-With": "XMLHttpRequest"})
    return client


@pytest.fixture
def reader_client(client, reader_user):
    login(client, "lecteur", READER_PASSWORD)
    client.headers.update({"X-Requested-With": "XMLHttpRequest"})
    return client


def contract_payload(**overrides):
    data = {
        "name": "Licence antivirus",
        "supplier": "Éditeur SA",
        "category": "licence",
        "amount": 3600.0,
        "duration_months": 36,
        "start_date": "2024-01-01",
        "end_date": "2026-12-31",
        "notice_period_days": 90,
        "auto_renewal": True,
        "sharepoint_file_url": "https://exemple.sharepoint.com/contrat.pdf",
    }
    data.update(overrides)
    return data
