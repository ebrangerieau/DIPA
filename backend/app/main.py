"""
Application principale Cockpit IT.
Point d'entrée FastAPI avec configuration CORS et routes.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.routers import contracts_router, tickets_router, auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire de cycle de vie de l'application.
    Initialise la base de données au démarrage.
    """
    # Startup
    print("🚀 Initialisation de la base de données...")
    init_db()
    print("✅ Base de données initialisée")
    
    # Créer un utilisateur admin si l'authentification locale est activée
    if settings.enable_local_auth and settings.bootstrap_admin_username:
        from app.database import SessionLocal
        from app.models.user import User
        
        db = SessionLocal()
        try:
            existing_admin = db.query(User).filter(User.is_admin == True).first()
            if not existing_admin:
                admin = User(
                    username=settings.bootstrap_admin_username,
                    email=settings.bootstrap_admin_email,
                    hashed_password=User.hash_password(settings.bootstrap_admin_password),
                    full_name="Administrateur (bootstrap)",
                    is_admin=True,
                    is_active=True
                )
                db.add(admin)
                db.commit()
                print("👤 Utilisateur admin créé via bootstrap.")
        except Exception as e:
            print(f"⚠️  Erreur lors de la création de l'admin: {e}")
        finally:
            db.close()
    
    yield
    
    # Shutdown
    print("👋 Arrêt de l'application")


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API pour le pilotage visuel des contrats et projets IT",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routers
app.include_router(auth_router)
app.include_router(contracts_router)
app.include_router(tickets_router)


@app.get("/")
async def root():
    """
    Endpoint racine pour vérifier que l'API fonctionne.
    
    Returns:
        dict: Message de bienvenue
    """
    return {
        "message": f"Bienvenue sur {settings.app_name} API",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de santé pour les vérifications de disponibilité.
    
    Returns:
        dict: Statut de santé
    """
    return {
        "status": "healthy",
        "service": settings.app_name
    }
