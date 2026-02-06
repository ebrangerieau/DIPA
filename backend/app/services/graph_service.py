"""
Service pour interagir avec Microsoft Graph API.
Gère l'authentification SSO et l'accès aux fichiers SharePoint.
"""
import msal
import httpx
from typing import Dict, Optional
from app.config import settings


class GraphService:
    """
    Service pour interagir avec Microsoft Graph API.
    Gère l'authentification via Entra ID (Azure AD) et l'accès aux ressources.
    """
    
    def __init__(self):
        self.client_id = settings.azure_client_id
        self.client_secret = settings.azure_client_secret
        self.authority = settings.azure_authority_url
        self.redirect_uri = settings.azure_redirect_uri
        self.graph_endpoint = settings.graph_api_endpoint
        
        # Scopes pour l'authentification
        self.scopes = [
            "User.Read",
            "Files.Read.All",
            "Sites.Read.All"
        ]
        
        # Création de l'application MSAL
        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
    
    def get_auth_url(self, state: str = None) -> str:
        """
        Génère l'URL d'authentification pour rediriger l'utilisateur.
        
        Args:
            state: État optionnel pour la sécurité CSRF
        
        Returns:
            str: URL d'authentification
        """
        auth_url = self.app.get_authorization_request_url(
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
            state=state
        )
        return auth_url
    
    async def authenticate_user(self, authorization_code: str) -> Dict:
        """
        Authentifie l'utilisateur avec le code d'autorisation OAuth.
        
        Args:
            authorization_code: Code d'autorisation reçu du callback
        
        Returns:
            Dict: Informations du token (access_token, id_token, etc.)
        
        Raises:
            Exception: En cas d'erreur d'authentification
        """
        result = self.app.acquire_token_by_authorization_code(
            authorization_code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        if "error" in result:
            raise Exception(f"Erreur d'authentification: {result.get('error_description')}")
        
        return result
    
    async def get_user_info(self, access_token: str) -> Dict:
        """
        Récupère les informations de l'utilisateur connecté.
        
        Args:
            access_token: Token d'accès Microsoft
        
        Returns:
            Dict: Informations utilisateur (displayName, mail, etc.)
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.graph_endpoint}/me",
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_file_content(self, access_token: str, file_url: str) -> bytes:
        """
        Récupère le contenu d'un fichier depuis SharePoint.
        
        Args:
            access_token: Token d'accès Microsoft
            file_url: URL du fichier SharePoint
        
        Returns:
            bytes: Contenu du fichier
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                file_url,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.content
    
    async def get_sharepoint_file_metadata(
        self, 
        access_token: str, 
        site_id: str, 
        file_path: str
    ) -> Dict:
        """
        Récupère les métadonnées d'un fichier SharePoint.
        
        Args:
            access_token: Token d'accès Microsoft
            site_id: ID du site SharePoint
            file_path: Chemin du fichier
        
        Returns:
            Dict: Métadonnées du fichier
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        endpoint = f"{self.graph_endpoint}/sites/{site_id}/drive/root:/{file_path}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                endpoint,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Rafraîchit le token d'accès.
        
        Args:
            refresh_token: Token de rafraîchissement
        
        Returns:
            Dict: Nouveau token d'accès
        """
        result = self.app.acquire_token_by_refresh_token(
            refresh_token,
            scopes=self.scopes
        )
        
        if "error" in result:
            raise Exception(f"Erreur de rafraîchissement: {result.get('error_description')}")
        
        return result
