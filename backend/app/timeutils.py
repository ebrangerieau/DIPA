"""
Utilitaires de dates : « aujourd'hui » dans le fuseau de l'établissement et calculs de mois.
"""
import calendar
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def local_now() -> datetime:
    return datetime.now(local_tz())


def today() -> date:
    """Date du jour dans le fuseau configuré (et non en UTC, fuseau du conteneur)."""
    return local_now().date()


def utcnow() -> datetime:
    """Horodatage UTC naïf, format historique des colonnes DateTime de la base."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_local_date(value: datetime) -> date:
    """Convertit un horodatage (UTC s'il est naïf) en date locale."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(local_tz()).date()


def add_months(start: date, months: int) -> date:
    """Ajoute des mois en ramenant au dernier jour du mois si nécessaire (31/01 + 1 mois = 28/02)."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def period_end(start: date, months: int) -> date:
    """Dernier jour d'une période de `months` mois commençant le `start` (du 01/09 au 31/08)."""
    return add_months(start, months) - timedelta(days=1)
