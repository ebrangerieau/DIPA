"""
Configuration de l'application Cockpit IT.
Gestion centralisée des variables d'environnement (fichier .env ou environnement).
"""
import json
import os
from typing import Annotated, Optional

import re

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

APP_VERSION = "1.1.0"  # Version du code (volontairement non surchargeable par le .env)
DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"

# Marqueurs signalant une valeur d'exemple laissée telle quelle dans le .env
_PLACEHOLDER_MARKERS = ("votre", "your", "change", "example", "exemple", "xxx")


def _is_configured(value: Optional[str]) -> bool:
    """Indique si une valeur est renseignée et n'est pas un exemple du .env.example."""
    if not value or not value.strip():
        return False
    lowered = value.lower()
    return not any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _split_list(value):
    """Accepte une liste JSON (["a","b"]) ou une liste séparée par des virgules (a,b)."""
    if value is None:
        return []
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        if value.startswith("["):
            return json.loads(value)
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CsvList = Annotated[list[str], NoDecode]
CsvIntList = Annotated[list[int], NoDecode]


class Settings(BaseSettings):
    """Configuration de l'application."""

    # Application
    app_name: str = "Cockpit IT"
    debug: bool = False
    sql_echo: bool = False
    timezone: str = "Europe/Paris"
    # URL publique de l'application (liens dans les e-mails), ex. https://cockpit.mondomaine.fr
    app_public_url: str = ""
    # URL de redirection après connexion SSO. Vide = racine de l'origine courante ("/").
    frontend_url: str = ""

    # Authentification
    enable_local_auth: bool = True  # True = comptes locaux autorisés, False = SSO uniquement
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    session_cookie_name: str = "cockpit_session"
    cookie_secure: Optional[bool] = None  # None = automatique (cookies sécurisés hors DEBUG)
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15

    # Bootstrap admin (optionnel, uniquement si aucun administrateur n'existe)
    bootstrap_admin_username: Optional[str] = None
    bootstrap_admin_email: Optional[str] = None
    bootstrap_admin_password: Optional[str] = None

    # Base de données
    database_url: str = "postgresql://cockpit:cockpit_password@postgres:5432/cockpit_db"

    # API Zammad
    zammad_api_url: str = ""
    zammad_api_token: str = ""
    zammad_public_url: str = ""  # URL vue par les navigateurs (défaut : ZAMMAD_API_URL)
    zammad_project_tag: str = "#Projet"
    zammad_cache_seconds: int = 300
    zammad_timeout_seconds: float = 30.0

    # Microsoft Entra ID (SSO)
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_authority: Optional[str] = None
    azure_redirect_uri: str = "http://localhost:5173/api/auth/callback"
    sso_scopes: CsvList = ["User.Read"]
    sso_auto_activate: bool = False  # False = un admin doit valider chaque nouveau compte SSO
    sso_admin_emails: CsvList = []
    sso_admin_roles: CsvList = ["Cockpit.Admin"]
    sso_allowed_roles: CsvList = []  # vide = pas de restriction par rôle d'application

    # Microsoft Graph API
    graph_api_endpoint: str = "https://graph.microsoft.com/v1.0"
    sharepoint_site_url: str = ""

    # Alertes e-mail sur les échéances de contrats
    alerts_enabled: bool = False
    alert_recipients: CsvList = []
    alert_days_before_deadline: CsvIntList = [60, 30, 7]
    alert_end_days: int = 30
    alert_hour: int = 7
    mail_backend: str = "none"  # none | smtp | graph
    mail_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False

    # Tâches planifiées (alertes, reconductions tacites)
    scheduler_enabled: bool = True

    # CORS (utile seulement si le frontend est servi depuis une autre origine que l'API)
    cors_origins: CsvList = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        # COCKPIT_ENV_FILE vide = aucun fichier lu (tests hermétiques)
        env_file=os.environ.get("COCKPIT_ENV_FILE", ".env") or None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator(
        "sso_scopes", "sso_admin_emails", "sso_admin_roles", "sso_allowed_roles",
        "alert_recipients", "alert_days_before_deadline", "cors_origins",
        mode="before",
    )
    @classmethod
    def _parse_lists(cls, value):
        return _split_list(value)

    @field_validator(
        "bootstrap_admin_username", "bootstrap_admin_email", "bootstrap_admin_password",
        "cookie_secure", "azure_authority",
        mode="before",
    )
    @classmethod
    def _empty_is_none(cls, value):
        """Une variable laissée vide dans le .env vaut « non renseignée »."""
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("mail_backend")
    @classmethod
    def _check_mail_backend(cls, value: str) -> str:
        value = (value or "none").strip().lower()
        if value not in {"none", "smtp", "graph"}:
            raise ValueError("MAIL_BACKEND doit valoir none, smtp ou graph.")
        return value

    @property
    def app_version(self) -> str:
        return APP_VERSION

    @property
    def azure_authority_url(self) -> str:
        """Construit l'URL d'autorité Entra ID."""
        if self.azure_authority:
            return self.azure_authority
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"

    @property
    def sso_enabled(self) -> bool:
        """Le SSO n'est proposé que si l'App Registration est réellement configurée."""
        return all(
            _is_configured(v)
            for v in (self.azure_tenant_id, self.azure_client_id, self.azure_client_secret)
        )

    @property
    def zammad_configured(self) -> bool:
        return _is_configured(self.zammad_api_url) and _is_configured(self.zammad_api_token)

    @property
    def cookie_secure_effective(self) -> bool:
        return (not self.debug) if self.cookie_secure is None else self.cookie_secure

    @property
    def mail_configured(self) -> bool:
        if not _is_configured(self.mail_from):
            return False
        if self.mail_backend == "smtp":
            return _is_configured(self.smtp_host)
        if self.mail_backend == "graph":
            return self.sso_enabled
        return False

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Valide les paramètres de sécurité sensibles."""
        if not self.debug and (self.secret_key == DEFAULT_SECRET_KEY or len(self.secret_key) < 32):
            raise ValueError(
                "SECRET_KEY doit être définie (32 caractères minimum) hors mode DEBUG. "
                "Générez-la avec : openssl rand -hex 32"
            )

        bootstrap_values = [
            self.bootstrap_admin_username,
            self.bootstrap_admin_email,
            self.bootstrap_admin_password,
        ]
        if any(bootstrap_values) and not all(bootstrap_values):
            raise ValueError(
                "Les variables BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_EMAIL et "
                "BOOTSTRAP_ADMIN_PASSWORD doivent être toutes renseignées."
            )
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError("BOOTSTRAP_ADMIN_PASSWORD doit contenir au moins 12 caractères.")
        if self.bootstrap_admin_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", self.bootstrap_admin_email):
            raise ValueError("BOOTSTRAP_ADMIN_EMAIL n'est pas une adresse e-mail valide.")
        if not 0 <= self.alert_hour <= 23:
            raise ValueError("ALERT_HOUR doit être compris entre 0 et 23.")
        return self


# Instance globale de configuration
settings = Settings()
