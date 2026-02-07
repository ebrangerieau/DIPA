"""
Configuration de l'application Cockpit IT.
Gestion centralisée des variables d'environnement.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, model_validator
from typing import Optional


class Settings(BaseSettings):
    """Configuration de l'application."""
    
    # Application
    app_name: str = "Cockpit IT"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Authentification
    enable_local_auth: bool = True  # True = auth locale, False = SSO uniquement
    
    # Base de données PostgreSQL
    database_url: str = "postgresql://cockpit:cockpit@postgres:5432/cockpit_db"
    
    # API Zammad
    zammad_api_url: str
    zammad_api_token: str
    zammad_project_tag: str = "#Projet"
    
    # Microsoft Entra ID (Azure AD)
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_authority: Optional[str] = None
    azure_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # Microsoft Graph API
    graph_api_endpoint: str = "https://graph.microsoft.com/v1.0"
    sharepoint_site_url: str
    
    # JWT pour l'authentification
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Bootstrap admin (optionnel)
    bootstrap_admin_username: Optional[str] = None
    bootstrap_admin_email: Optional[EmailStr] = None
    bootstrap_admin_password: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def azure_authority_url(self) -> str:
        """Construit l'URL d'autorité Azure AD."""
        if self.azure_authority:
            return self.azure_authority
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        """Valide les paramètres de sécurité sensibles."""
        if not self.debug and self.secret_key == "your-secret-key-change-in-production":
            raise ValueError(
                "La variable SECRET_KEY doit être définie en production."
            )

        bootstrap_values = [
            self.bootstrap_admin_username,
            self.bootstrap_admin_email,
            self.bootstrap_admin_password,
        ]
        if any(bootstrap_values) and not all(bootstrap_values):
            raise ValueError(
                "Les variables BOOTSTRAP_ADMIN_USERNAME, "
                "BOOTSTRAP_ADMIN_EMAIL et BOOTSTRAP_ADMIN_PASSWORD "
                "doivent être toutes renseignées."
            )
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError(
                "BOOTSTRAP_ADMIN_PASSWORD doit contenir au moins 12 caractères."
            )
        return self


# Instance globale de configuration
settings = Settings()
