"""
Service d'accès à l'API Zammad (lecture seule).

Comportements constatés sur l'instance réelle et pris en compte ici :
- la recherche renvoie au plus 200 tickets par page : il faut paginer (page / per_page) ;
- l'état se filtre avec `state.name:closed` (la syntaxe `state:closed` ne renvoie rien) ;
- les états personnalisés (« En attente de livraison »...) sont classés via leur type ;
- les tickets renvoyés par la recherche ne contiennent pas leurs tags ;
- `last_close_at` donne la dernière clôture (un ticket peut avoir été réouvert).
"""
import asyncio
import logging
import statistics
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

import httpx

from app import timeutils
from app.config import settings
from app.schemas.tickets import Ticket, TicketStats

logger = logging.getLogger(__name__)

PAGE_SIZE = 200
MAX_PAGES = 50
UNASSIGNED_OWNER_ID = 1  # Utilisateur système « - » de Zammad (ticket non assigné)
STATE_TYPE_CLOSED = 5
STATE_TYPES_FINISHED = {5, 6, 7}  # closed, merged, removed
DEFAULT_STATE_TYPES = {"new": 1, "open": 2, "pending reminder": 3, "pending close": 4, "closed": 5, "merged": 6}
STATES_CACHE_SECONDS = 3600
USERS_CACHE_SECONDS = 3600


class ZammadError(Exception):
    """Zammad est injoignable, refuse l'accès ou renvoie une erreur."""


class _TTLCache:
    """Cache mémoire simple avec expiration (une seule instance d'API)."""

    def __init__(self):
        self._data: dict = {}

    def get(self, key):
        entry = self._data.get(key)
        if entry and entry[0] > time.monotonic():
            return entry[1]
        return None

    def set(self, key, value, ttl: float) -> None:
        self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._data.clear()


_cache = _TTLCache()


def clear_cache() -> None:
    _cache.clear()


def parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _extract_tickets(data) -> list:
    """La recherche renvoie une liste (expand=true) ou un dict « assets » (expand=false)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("assets", {}).get("Ticket", {}).values())
    return []


def _quoted_or(values: Iterable[str]) -> str:
    return " OR ".join('"' + v.replace('"', '\\"') + '"' for v in values)


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


class ZammadService:
    """Accès à Zammad : tickets #Projet (timeline), statistiques et indicateurs du support."""

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.api_url = settings.zammad_api_url.rstrip("/")
        self.public_url = (settings.zammad_public_url or settings.zammad_api_url).rstrip("/")
        self.project_tag = settings.zammad_project_tag
        self._transport = transport  # Injection d'un transport factice pour les tests

    # ---------- Accès HTTP ----------

    @property
    def project_query(self) -> str:
        return f'tags:"{self.project_tag}"'

    def ticket_url(self, ticket_id: int) -> str:
        return f"{self.public_url}/#ticket/zoom/{ticket_id}"

    def _client(self) -> httpx.AsyncClient:
        if not settings.zammad_configured:
            raise ZammadError("Zammad n'est pas configuré (ZAMMAD_API_URL / ZAMMAD_API_TOKEN)")
        return httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": f"Token token={settings.zammad_api_token}",
                "Accept": "application/json",
            },
            timeout=settings.zammad_timeout_seconds,
            transport=self._transport,
        )

    async def _get(self, client: httpx.AsyncClient, path: str, params: Optional[dict] = None):
        try:
            response = await client.get(path, params=params)
        except httpx.HTTPError as exc:
            logger.warning("Zammad injoignable (%s) : %s", path, exc)
            raise ZammadError("Zammad est injoignable") from exc
        if response.status_code in (401, 403):
            raise ZammadError("Accès refusé par Zammad : vérifiez le token API et ses droits")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            logger.warning("Erreur Zammad HTTP %s sur %s", response.status_code, path)
            raise ZammadError(f"Erreur Zammad (HTTP {response.status_code})")
        try:
            return response.json()
        except ValueError as exc:
            raise ZammadError("Réponse Zammad illisible") from exc

    async def search(self, query: str) -> list[dict]:
        """Recherche paginée : renvoie tous les tickets correspondant à la requête."""
        key = ("search", self.api_url, query)
        cached = _cache.get(key)
        if cached is not None:
            return cached

        results: list[dict] = []
        seen: set = set()
        async with self._client() as client:
            for page in range(1, MAX_PAGES + 1):
                data = await self._get(client, "/api/v1/tickets/search", {
                    "query": query,
                    "page": page,
                    "per_page": PAGE_SIZE,
                    "expand": "true",
                    "sort_by": "created_at",
                    "order_by": "asc",
                })
                batch = [t for t in _extract_tickets(data) if isinstance(t, dict) and "id" in t]
                fresh = [t for t in batch if t["id"] not in seen]
                results.extend(fresh)
                seen.update(t["id"] for t in fresh)
                if len(batch) < PAGE_SIZE or not fresh:
                    break
            else:
                logger.warning("Recherche Zammad tronquée à %s tickets : %s", len(results), query)

        _cache.set(key, results, settings.zammad_cache_seconds)
        return results

    # ---------- Référentiels ----------

    async def state_types(self) -> dict[str, int]:
        """Nom d'état -> type d'état (1 nouveau ... 5 clos, 6 fusionné, 7 supprimé)."""
        key = ("states", self.api_url)
        cached = _cache.get(key)
        if cached is not None:
            return cached
        async with self._client() as client:
            data = await self._get(client, "/api/v1/ticket_states")
        mapping = {
            s["name"]: s.get("state_type_id")
            for s in (data or [])
            if isinstance(s, dict) and s.get("name") and s.get("active", True)
        } or dict(DEFAULT_STATE_TYPES)
        _cache.set(key, mapping, STATES_CACHE_SECONDS)
        return mapping

    async def closed_state_names(self) -> list[str]:
        types = await self.state_types()
        return sorted(n for n, t in types.items() if t == STATE_TYPE_CLOSED) or ["closed"]

    async def finished_state_names(self) -> list[str]:
        types = await self.state_types()
        return sorted(n for n, t in types.items() if t in STATE_TYPES_FINISHED) or ["closed", "merged"]

    async def user_names(self, user_ids: Iterable) -> dict[int, str]:
        """Nom affichable (prénom nom) des agents, mis en cache une heure."""
        ids = {i for i in user_ids if i and i != UNASSIGNED_OWNER_ID}
        names: dict[int, str] = {}
        missing = []
        for user_id in ids:
            cached = _cache.get(("user", self.api_url, user_id))
            if cached:
                names[user_id] = cached
            else:
                missing.append(user_id)
        if missing:
            async with self._client() as client:
                responses = await asyncio.gather(
                    *(self._get(client, f"/api/v1/users/{user_id}") for user_id in missing),
                    return_exceptions=True,
                )
            for user_id, data in zip(missing, responses, strict=True):
                if isinstance(data, dict):
                    name = " ".join(p for p in (data.get("firstname"), data.get("lastname")) if p).strip()
                    names[user_id] = name or data.get("login") or f"Agent {user_id}"
                    _cache.set(("user", self.api_url, user_id), names[user_id], USERS_CACHE_SECONDS)
        return names

    # ---------- Conversion ----------

    def to_ticket(
        self,
        raw: dict,
        *,
        finished_states: Iterable[str],
        owner_names: Optional[dict] = None,
        tags: Optional[list] = None,
    ) -> Ticket:
        owner_id = raw.get("owner_id")
        owner = None
        if owner_id and owner_id != UNASSIGNED_OWNER_ID:
            owner = (owner_names or {}).get(owner_id) or raw.get("owner")
        state = str(raw.get("state") or "inconnu")
        closed_at = None
        if state in set(finished_states):
            closed_at = parse_dt(raw.get("last_close_at") or raw.get("close_at"))
        created_at = parse_dt(raw.get("created_at")) or datetime.now(timezone.utc)
        return Ticket(
            id=raw["id"],
            number=str(raw["number"]) if raw.get("number") else None,
            title=raw.get("title") or f"Ticket {raw['id']}",
            state=state,
            priority=str(raw.get("priority") or "2 normal"),
            tags=list(tags if tags is not None else raw.get("tags") or []),
            created_at=created_at,
            updated_at=parse_dt(raw.get("updated_at")) or created_at,
            close_at=closed_at,
            owner_id=owner_id,
            owner=owner,
            group=raw.get("group"),
            url=self.ticket_url(raw["id"]),
        )

    # ---------- Cas d'usage ----------

    async def get_project_tickets(self) -> list[Ticket]:
        """Tickets portant le tag projet (affichés sur la timeline)."""
        raws = await self.search(self.project_query)
        finished = await self.finished_state_names()
        names = await self.user_names(r.get("owner_id") for r in raws)
        return [
            self.to_ticket(r, finished_states=finished, owner_names=names, tags=[self.project_tag])
            for r in raws
        ]

    async def get_closed_tickets_stats(
        self,
        start_date: date,
        end_date: date,
        exclude_project_tag: bool = True,
    ) -> list[TicketStats]:
        """Nombre de tickets clos par jour (heure locale), hors tickets projet par défaut."""
        closed = await self.closed_state_names()
        # Marge d'un jour : Zammad stocke en UTC, le regroupement se fait en heure locale
        low = (start_date - timedelta(days=1)).isoformat()
        high = (end_date + timedelta(days=1)).isoformat()
        query = (
            f"state.name:({_quoted_or(closed)}) AND "
            f"(close_at:[{low} TO {high}] OR last_close_at:[{low} TO {high}])"
        )
        if exclude_project_tag:
            query += f" AND NOT {self.project_query}"

        counts: Counter = Counter()
        for raw in await self.search(query):
            closed_at = parse_dt(raw.get("last_close_at") or raw.get("close_at"))
            if not closed_at:
                continue
            day = timeutils.to_local_date(closed_at)
            if start_date <= day <= end_date:
                counts[day] += 1
        return [TicketStats(date=day.isoformat(), count=n) for day, n in sorted(counts.items())]

    async def get_ticket_by_id(self, ticket_id: int) -> Optional[Ticket]:
        finished = await self.finished_state_names()
        async with self._client() as client:
            raw = await self._get(client, f"/api/v1/tickets/{ticket_id}", {"expand": "true"})
            if not isinstance(raw, dict):
                return None
            tags_data = await self._get(client, "/api/v1/tags", {"object": "Ticket", "o_id": ticket_id})
        tags = tags_data.get("tags", []) if isinstance(tags_data, dict) else []
        names = await self.user_names([raw.get("owner_id")])
        return self.to_ticket(raw, finished_states=finished, owner_names=names, tags=tags)

    async def get_ticket_kpis(self, weeks: int = 12) -> dict:
        """Indicateurs du support : backlog, charge par technicien, flux, délai de résolution."""
        today = timeutils.today()
        since = today - timedelta(days=max(90, weeks * 7))
        closed = await self.closed_state_names()
        finished = await self.finished_state_names()

        open_raw, created_raw, closed_raw, project_raw = await asyncio.gather(
            self.search(f"NOT state.name:({_quoted_or(finished)})"),
            self.search(f"created_at:>={since.isoformat()}"),
            self.search(
                f"state.name:({_quoted_or(closed)}) AND "
                f"(close_at:>={since.isoformat()} OR last_close_at:>={since.isoformat()})"
            ),
            self.search(self.project_query),
        )

        names = await self.user_names(r.get("owner_id") for r in open_raw)
        open_tickets = [self.to_ticket(r, finished_states=finished, owner_names=names) for r in open_raw]
        now = datetime.now(timezone.utc)
        ages = [(now - t.created_at).days for t in open_tickets]

        window_30 = today - timedelta(days=30)
        created_days = [timeutils.to_local_date(parse_dt(r["created_at"])) for r in created_raw if r.get("created_at")]
        closed_pairs = []
        for r in closed_raw:
            closed_at = parse_dt(r.get("last_close_at") or r.get("close_at"))
            created_at = parse_dt(r.get("created_at"))
            if closed_at:
                closed_pairs.append((timeutils.to_local_date(closed_at), created_at, closed_at))
        closed_days = [day for day, _, _ in closed_pairs]

        resolution_hours = [
            (closed_at - created_at).total_seconds() / 3600
            for day, created_at, closed_at in closed_pairs
            if created_at and day > today - timedelta(days=90) and closed_at >= created_at
        ]

        first_week = _week_start(today) - timedelta(weeks=weeks - 1)
        weekly = []
        for index in range(weeks):
            start = first_week + timedelta(weeks=index)
            end = start + timedelta(days=6)
            weekly.append({
                "week_start": start.isoformat(),
                "label": f"S{start.isocalendar().week:02d}",
                "created": sum(1 for d in created_days if start <= d <= end),
                "closed": sum(1 for d in closed_days if start <= d <= end),
            })

        by_owner = Counter(t.owner or "Non assigné" for t in open_tickets)
        oldest = sorted(open_tickets, key=lambda t: t.created_at)[:5]
        return {
            "open_count": len(open_tickets),
            "unassigned_count": sum(1 for t in open_tickets if not t.owner),
            "high_priority_open": sum(1 for t in open_tickets if t.priority.startswith("3")),
            "older_than_30d": sum(1 for a in ages if a > 30),
            "created_30d": sum(1 for d in created_days if d > window_30),
            "closed_30d": sum(1 for d in closed_days if d > window_30),
            "median_resolution_hours": round(statistics.median(resolution_hours), 1) if resolution_hours else None,
            "project_open_count": sum(1 for r in project_raw if r.get("state") not in set(finished)),
            "by_owner": [{"owner": o, "count": n} for o, n in by_owner.most_common()],
            "by_state": [{"state": s, "count": n} for s, n in Counter(t.state for t in open_tickets).most_common()],
            "oldest_open": [
                {
                    "id": t.id,
                    "number": t.number,
                    "title": t.title,
                    "owner": t.owner,
                    "state": t.state,
                    "age_days": (now - t.created_at).days,
                    "url": t.url,
                }
                for t in oldest
            ],
            "weekly_flow": weekly,
        }

    async def check_connection(self) -> None:
        """Vérifie l'accès à Zammad (lève ZammadError sinon)."""
        async with self._client() as client:
            me = await self._get(client, "/api/v1/users/me")
        if not isinstance(me, dict):
            raise ZammadError("Réponse Zammad inattendue")
