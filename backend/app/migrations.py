"""
Exécution automatique des migrations SQL au démarrage.

Principe : `create_all` crée les tables absentes avec le schéma courant, puis chaque
fichier `migrations/NNN_*.sql` non encore appliqué est exécuté une seule fois et
enregistré dans la table `schema_migrations`. Les scripts sont idempotents
(IF NOT EXISTS) pour rester sans effet sur une base neuve.
"""
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def run_migrations(engine: Engine) -> list[str]:
    """Applique les migrations en attente et retourne la liste des versions appliquées."""
    if engine.dialect.name != "postgresql":
        # SQLite (tests, dev) : create_all a déjà construit le schéma complet.
        return []

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version VARCHAR(255) PRIMARY KEY,"
            " applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        ))
        applied = {row[0] for row in conn.execute(text("SELECT version FROM schema_migrations"))}

    newly_applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
            conn.execute(text("INSERT INTO schema_migrations (version) VALUES (:v)"), {"v": version})
        logger.info("Migration appliquée : %s", version)
        newly_applied.append(version)
    return newly_applied
