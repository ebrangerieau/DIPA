"""
Application principale Cockpit IT.
Point d'entrée FastAPI : configuration, sécurité, routes et tâches planifiées.

Toutes les routes sont servies sous /api : le frontend (Nginx en production, Vite en
développement) relaie /api vers le backend, l'application et l'API partagent donc la
même origine (cookies de session simples, pas de CORS nécessaire).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import scheduler
from app.config import settings
from app.database import SessionLocal, init_db
from app.services.zammad_service import ZammadError

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s : %(message)s",
)
for noisy in ("httpx", "httpcore", "msal", "asyncio"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger = logging.getLogger("cockpit")


def bootstrap_admin() -> None:
    """Crée l'administrateur initial (variables BOOTSTRAP_ADMIN_*) si aucun n'existe."""
    if not (settings.enable_local_auth and settings.bootstrap_admin_username):
        return
    from app.models.user import User
    from app.security import password_policy_error

    error = password_policy_error(settings.bootstrap_admin_password)
    if error:
        logger.error("Administrateur initial non créé : BOOTSTRAP_ADMIN_PASSWORD refusé (%s)", error)
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.is_admin.is_(True)).first():
            return
        db.add(User(
            username=settings.bootstrap_admin_username,
            email=str(settings.bootstrap_admin_email).lower(),
            hashed_password=User.hash_password(settings.bootstrap_admin_password),
            full_name="Administrateur",
            is_admin=True,
            is_active=True,
            auth_provider="local",
            must_change_password=True,
        ))
        db.commit()
        logger.info("Administrateur initial créé (mot de passe à changer à la première connexion)")
    except Exception:
        db.rollback()
        logger.exception("Création de l'administrateur initial impossible")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la base, l'administrateur initial et les tâches planifiées."""
    init_db()
    logger.info("Base de données initialisée")
    bootstrap_admin()
    if not settings.zammad_configured:
        logger.warning("Zammad n'est pas configuré : les indicateurs tickets seront indisponibles")
    task = scheduler.start()
    yield
    await scheduler.stop(task)
    logger.info("Arrêt de l'application")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API pour le pilotage visuel des contrats et projets IT",
    lifespan=lifespan,
    docs_url="/api/docs",
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

# CORS : utile uniquement si le frontend est servi depuis une autre origine
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    if request.url.path.startswith("/api/") and not request.url.path.startswith("/api/docs"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(ZammadError)
async def zammad_error_handler(request: Request, exc: ZammadError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


_FIELD_LABELS = {
    "name": "Nom", "supplier": "Fournisseur", "amount": "Montant", "duration_months": "Durée",
    "start_date": "Date de début", "end_date": "Date de fin", "notice_period_days": "Préavis",
    "sharepoint_file_url": "Lien SharePoint", "category": "Catégorie", "notes": "Notes",
    "username": "Identifiant", "email": "E-mail", "password": "Mot de passe",
}


def _french_message(error: dict) -> str:
    field = next((str(p) for p in reversed(error.get("loc", ())) if isinstance(p, str) and p != "body"), "")
    label = _FIELD_LABELS.get(field, field)
    ctx = error.get("ctx") or {}
    kind = error.get("type", "")
    if kind == "value_error":
        message = str(ctx.get("error") or error.get("msg", "")).removeprefix("Value error, ")
    elif kind == "missing":
        message = "champ obligatoire"
    elif kind in ("string_too_short",):
        message = "valeur trop courte"
    elif kind in ("string_too_long",):
        message = "valeur trop longue"
    elif kind in ("greater_than_equal", "greater_than"):
        message = f"doit être supérieur ou égal à {ctx.get('ge', ctx.get('gt'))}"
    elif kind in ("less_than_equal", "less_than"):
        message = f"doit être inférieur ou égal à {ctx.get('le', ctx.get('lt'))}"
    elif kind.startswith(("date", "datetime")):
        message = "date invalide"
    elif kind == "literal_error":
        message = "valeur non autorisée"
    else:
        message = error.get("msg", "valeur invalide")
    return f"{label} : {message}" if label else message


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail = " ; ".join(dict.fromkeys(_french_message(e) for e in errors)) or "Requête invalide"
    return JSONResponse(status_code=422, content={"detail": detail})


# Enregistrement des routers sous /api
from app.routers import auth, contracts, dashboard, system, tickets, users  # noqa: E402

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(users.router)
api.include_router(contracts.router)
api.include_router(tickets.router)
api.include_router(dashboard.router)
api.include_router(system.router)


@api.get("/health", tags=["système"])
def health_check():
    """Endpoint de santé (supervision, healthcheck Docker)."""
    return {"status": "healthy", "service": settings.app_name, "version": settings.app_version}


app.include_router(api)
