"""
Tests du service Zammad et des routes tickets (serveur Zammad simulé).
"""
import asyncio

import pytest

from app.main import app
from app.routers.tickets import get_zammad_service
from app.services.zammad_service import ZammadError
from tests.zammad_fake import FakeZammad, ticket


def run(coro):
    return asyncio.run(coro)


def test_search_paginates_beyond_200_results():
    tickets = [ticket(i) for i in range(1, 451)]
    fake = FakeZammad(lambda q: tickets)
    results = run(fake.service().search("created_at:>=2026-01-01"))
    assert len(results) == 450
    pages = [r.url.params["page"] for r in fake.requests if r.url.path == "/api/v1/tickets/search"]
    assert pages == ["1", "2", "3"]
    assert fake.requests[0].url.params["per_page"] == "200"
    assert fake.requests[0].headers["authorization"] == "Token token=token-de-test"


def test_search_results_are_cached():
    fake = FakeZammad(lambda q: [ticket(1)])
    service = fake.service()
    run(service.search("q"))
    run(service.search("q"))
    assert len(fake.queries()) == 1


def test_closed_stats_use_local_day_and_exclude_projects():
    closed = [
        # 23h30 UTC le 21/09 = 01h30 le 22/09 à Paris
        ticket(1, state="closed", close_at="2026-09-21T23:30:00Z"),
        ticket(2, state="closed", close_at="2026-09-21T10:00:00Z"),
        # Réouvert puis reclôturé : la dernière clôture fait foi
        ticket(3, state="closed", close_at="2026-08-01T10:00:00Z", last_close_at="2026-09-21T11:00:00Z"),
        ticket(4, state="closed", close_at="2026-09-30T10:00:00Z"),  # Hors période
    ]
    fake = FakeZammad(lambda q: closed)
    stats = run(fake.service().get_closed_tickets_stats(
        __import__("datetime").date(2026, 9, 1), __import__("datetime").date(2026, 9, 22)))
    assert [(s.date, s.count) for s in stats] == [("2026-09-21", 2), ("2026-09-22", 1)]
    query = fake.queries()[0]
    assert query.startswith('state.name:("closed") AND (close_at:[2026-08-31 TO 2026-09-23]')
    assert query.endswith('AND NOT tags:"#Projet"')


def test_project_tickets_and_timeline(admin_client):
    projects = [
        ticket(5, state="open", created_at="2026-06-01T08:00:00Z", owner_id=11, title="Migration Wi-Fi"),
        ticket(6, state="closed", created_at="2026-03-01T08:00:00Z", close_at="2026-05-15T08:00:00Z", owner_id=1),
    ]
    fake = FakeZammad(lambda q: projects if q == 'tags:"#Projet"' else [])
    app.dependency_overrides[get_zammad_service] = fake.service
    try:
        items = admin_client.get("/api/tickets/timeline/data").json()
    finally:
        del app.dependency_overrides[get_zammad_service]

    by_id = {i["id"]: i for i in items}
    wifi = by_id["ticket-5"]
    assert wifi["group"] == "projects" and wifi["color"] == "#3B82F6"
    assert wifi["metadata"]["owner"] == "Bruno Petit"
    assert wifi["metadata"]["url"] == "https://support.test/#ticket/zoom/5"
    assert wifi["metadata"]["close_at"] is None  # Ouvert : barre jusqu'à aujourd'hui
    closed = by_id["ticket-6"]
    assert closed["end"].startswith("2026-05-15")
    assert closed["metadata"]["owner"] is None  # Non assigné


def test_ticket_kpis():
    open_tickets = [
        ticket(1, state="open", created_at="2026-07-01T08:00:00Z", owner_id=10, priority="3 high"),
        ticket(2, state="En attente de livraison", created_at="2026-09-20T08:00:00Z", owner_id=10),
        ticket(3, state="new", created_at="2026-09-21T08:00:00Z", owner_id=1),
    ]
    closed = [
        ticket(4, state="closed", created_at="2026-09-10T08:00:00Z", close_at="2026-09-10T12:00:00Z"),
        ticket(5, state="closed", created_at="2026-09-01T08:00:00Z", close_at="2026-09-03T08:00:00Z"),
    ]

    def search(query):
        if query.startswith("NOT state.name:("):
            return open_tickets
        if query.startswith("created_at:>="):
            return open_tickets + closed
        if query.startswith("state.name:("):
            return closed
        return []

    fake = FakeZammad(search)
    kpis = run(fake.service().get_ticket_kpis())
    assert kpis["open_count"] == 3
    assert kpis["unassigned_count"] == 1
    assert kpis["high_priority_open"] == 1
    assert kpis["older_than_30d"] == 1
    assert kpis["closed_30d"] == 2
    assert kpis["median_resolution_hours"] == pytest.approx(26.0)  # médiane de 4 h et 48 h
    assert kpis["by_owner"][0] == {"owner": "Alice Martin", "count": 2}
    assert kpis["oldest_open"][0]["id"] == 1
    assert len(kpis["weekly_flow"]) == 12
    # L'état personnalisé est exclu via les types d'état et non par son nom
    assert '"En attente de livraison"' not in fake.queries()[0]
    assert '"closed"' in fake.queries()[0] and '"merged"' in fake.queries()[0]


def test_zammad_errors_are_explicit():
    with pytest.raises(ZammadError, match="token API"):
        run(FakeZammad(lambda q: [], status_code=401).service().search("x"))


def test_router_returns_502_when_zammad_fails(admin_client):
    fake = FakeZammad(lambda q: [], status_code=500)
    app.dependency_overrides[get_zammad_service] = fake.service
    try:
        response = admin_client.get("/api/tickets/stats")
    finally:
        del app.dependency_overrides[get_zammad_service]
    assert response.status_code == 502
    assert response.json()["detail"] == "Erreur Zammad (HTTP 500)"


def test_dashboard_survives_zammad_outage(admin_client):
    admin_client.post("/api/contracts", json={
        "name": "Box fibre", "supplier": "Opérateur", "amount": 600, "duration_months": 12,
        "start_date": "2025-11-01", "end_date": "2026-10-31", "notice_period_days": 60,
    })
    fake = FakeZammad(lambda q: [], status_code=503)
    app.dependency_overrides[get_zammad_service] = fake.service
    try:
        data = admin_client.get("/api/dashboard/summary").json()
    finally:
        del app.dependency_overrides[get_zammad_service]
    assert data["tickets"] is None
    assert data["tickets_error"] == "Erreur Zammad (HTTP 503)"
    assert data["contracts"]["in_notice"] == 1
    assert data["actions"][0]["name"] == "Box fibre"


def test_stats_period_is_bounded(admin_client):
    response = admin_client.get("/api/tickets/stats", params={"start_date": "2024-01-01", "end_date": "2026-01-01"})
    assert response.status_code == 400
