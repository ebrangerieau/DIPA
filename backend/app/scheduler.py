"""
Tâche planifiée interne : reconductions tacites et alertes e-mail.

Une vérification a lieu toutes les heures ; les traitements ne s'exécutent qu'à partir
de ALERT_HOUR (heure locale). Ils sont idempotents : une reconduction ne s'applique
qu'aux contrats échus et chaque alerte n'est envoyée qu'une fois (notification_log).
Prévu pour une seule instance de l'API (un seul worker uvicorn).
"""
import asyncio
import logging
from typing import Optional

from starlette.concurrency import run_in_threadpool

from app import timeutils
from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3600
STARTUP_DELAY_SECONDS = 60

state: dict = {"last_run": None, "last_result": None, "last_error": None}


def run_scheduled_jobs() -> Optional[dict]:
    from app.services import alerts_service
    from app.services.mail_service import MailError

    db = SessionLocal()
    try:
        result = alerts_service.run_alerts(db)
        state.update(last_run=timeutils.utcnow().isoformat(), last_result=result, last_error=None)
        return result
    except MailError as exc:
        state.update(last_run=timeutils.utcnow().isoformat(), last_error=str(exc))
        logger.warning("Alertes non envoyées : %s", exc)
    except Exception as exc:  # La boucle ne doit jamais s'arrêter
        state.update(last_run=timeutils.utcnow().isoformat(), last_error="Erreur interne (voir les journaux)")
        logger.exception("Échec de la tâche planifiée : %s", exc)
    finally:
        db.close()
    return None


async def _loop() -> None:
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    while True:
        if timeutils.local_now().hour >= settings.alert_hour:
            await run_in_threadpool(run_scheduled_jobs)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start() -> Optional[asyncio.Task]:
    if not settings.scheduler_enabled:
        logger.info("Tâches planifiées désactivées (SCHEDULER_ENABLED=false)")
        return None
    return asyncio.create_task(_loop(), name="cockpit-scheduler")


async def stop(task: Optional[asyncio.Task]) -> None:
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
