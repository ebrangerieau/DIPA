"""
Configuration de la base de données avec SQLAlchemy.
PostgreSQL en production ; SQLite accepté pour les tests et le développement rapide.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}  # Vérification de la connexion avant utilisation


engine = create_engine(settings.database_url, echo=settings.sql_echo, **_engine_options(settings.database_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base des modèles SQLAlchemy."""


def get_db():
    """
    Générateur de session de base de données pour les dépendances FastAPI.

    Yields:
        Session: Session SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialise la base de données : création des tables manquantes puis
    application des migrations SQL (PostgreSQL uniquement).
    """
    import app.models  # noqa: F401  (enregistrement des modèles dans Base.metadata)
    from app.migrations import run_migrations

    Base.metadata.create_all(bind=engine)
    run_migrations(engine)
