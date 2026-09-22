"""
Service Microsoft Entra ID / Graph API.
- Connexion SSO (flux « authorization code » avec PKCE, géré par MSAL) ;
- Envoi d'e-mails via Graph (permission d'application Mail.Send).
"""
import logging
from functools import lru_cache

import httpx
import msal

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_DEFAULT_SCOPE = ["https://graph.microsoft.com/.default"]


class SSOError(Exception):
    """Échec de l'authentification Microsoft (réponse invalide, refus, état CSRF)."""


class GraphMailError(Exception):
    """Échec d'envoi d'un e-mail via Graph."""


@lru_cache(maxsize=1)
def _msal_app() -> msal.ConfidentialClientApplication:
    # Créée à la demande : MSAL interroge l'autorité Microsoft lors de l'instanciation.
    return msal.ConfidentialClientApplication(
        settings.azure_client_id,
        authority=settings.azure_authority_url,
        client_credential=settings.azure_client_secret,
    )


class GraphService:
    """Accès à Microsoft Entra ID et à Microsoft Graph."""

    def __init__(self):
        if not settings.sso_enabled:
            raise SSOError("L'authentification Microsoft n'est pas configurée")
        self.app = _msal_app()
        self.graph_endpoint = settings.graph_api_endpoint.rstrip("/")

    # ---------- SSO ----------

    def initiate_login(self) -> dict:
        """Prépare le flux d'autorisation (state, nonce, PKCE) et l'URL Microsoft."""
        return self.app.initiate_auth_code_flow(
            scopes=settings.sso_scopes,
            redirect_uri=settings.azure_redirect_uri,
        )

    def complete_login(self, flow: dict, auth_response: dict) -> dict:
        """Échange le code d'autorisation et retourne les revendications (claims) de l'id_token."""
        try:
            result = self.app.acquire_token_by_auth_code_flow(flow, auth_response)
        except ValueError as exc:  # state absent ou différent : tentative rejouée ou falsifiée
            raise SSOError("Réponse d'authentification invalide") from exc
        if "error" in result:
            logger.warning("Refus Entra ID : %s", result.get("error_description") or result.get("error"))
            raise SSOError("Microsoft a refusé l'authentification")
        claims = result.get("id_token_claims") or {}
        if not claims.get("oid"):
            raise SSOError("Jeton Microsoft incomplet")
        return claims

    # ---------- E-mails ----------

    def _app_token(self) -> str:
        result = self.app.acquire_token_for_client(scopes=GRAPH_DEFAULT_SCOPE)
        if "access_token" not in result:
            logger.warning("Jeton Graph refusé : %s", result.get("error_description") or result.get("error"))
            raise GraphMailError("Impossible d'obtenir un jeton Microsoft Graph (vérifiez Mail.Send)")
        return result["access_token"]

    def send_mail(self, sender: str, recipients: list[str], subject: str, html_body: str) -> None:
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": r}} for r in recipients],
            },
            "saveToSentItems": False,
        }
        response = httpx.post(
            f"{self.graph_endpoint}/users/{sender}/sendMail",
            json=payload,
            headers={"Authorization": f"Bearer {self._app_token()}"},
            timeout=30.0,
        )
        if response.status_code >= 400:
            logger.warning("Envoi Graph refusé (HTTP %s)", response.status_code)
            raise GraphMailError(f"Envoi refusé par Microsoft Graph (HTTP {response.status_code})")
