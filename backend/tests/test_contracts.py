from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from datetime import date, timedelta

from app.main import app
from app.database import get_db, Base
from app.models.contract import Contract

# Configuration de la base de données de test en mémoire (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fixture pour la base de données
@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

# Override de la dépendance get_db
@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass # Session fermée par la fixture db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_read_contracts_empty(client):
    response = client.get("/contracts/")
    assert response.status_code == 200
    assert response.json() == []

def test_create_contract(client):
    contract_data = {
        "name": "Test Contract",
        "supplier": "Test Supplier",
        "amount": 1000.0,
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=365)),
        "notice_period_days": 90
    }
    response = client.post("/contracts/", json=contract_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Contract"
    assert "id" in data

def test_read_contract(client):
    # D'abord créer un contrat
    contract_data = {
        "name": "Contract to Read",
        "supplier": "Supplier A",
        "amount": 500.0,
        "start_date": str(date.today()),
        "end_date": str(date.today() + timedelta(days=100)),
        "notice_period_days": 30
    }
    create_res = client.post("/contracts/", json=contract_data)
    contract_id = create_res.json()["id"]

    # Ensuite le lire
    response = client.get(f"/contracts/{contract_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Contract to Read"

def test_create_contract_invalid_dates(client):
    contract_data = {
        "name": "Invalid Contract",
        "supplier": "Bad Supplier",
        "amount": 1000.0,
        "start_date": str(date.today()),
        "end_date": str(date.today() - timedelta(days=1)), # Fin avant début
        "notice_period_days": 90
    }
    response = client.post("/contracts/", json=contract_data)
    assert response.status_code == 400
