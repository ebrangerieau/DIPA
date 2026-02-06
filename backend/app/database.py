"""
Configuration de la base de données PostgreSQL avec SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Création du moteur SQLAlchemy
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Vérification de la connexion avant utilisation
    echo=settings.debug   # Log des requêtes SQL en mode debug
)

# Session locale
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles
Base = declarative_base()


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
    Initialise la base de données (création des tables).
    À appeler au démarrage de l'application.
    """
    Base.metadata.create_all(bind=engine)
