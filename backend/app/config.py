"""
Configuration de l'application Cockpit IT.
Gestion centralisée des variables d'environnement.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
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


# Instance globale de configuration
settings = Settings()
