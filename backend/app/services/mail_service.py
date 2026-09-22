"""
Envoi d'e-mails : SMTP (relais interne, fournisseur) ou Microsoft Graph (Microsoft 365).

Microsoft retire l'authentification basique SMTP d'Exchange Online : pour une boîte
Microsoft 365, préférer MAIL_BACKEND=graph (permission d'application Mail.Send).
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


class MailError(Exception):
    """L'e-mail n'a pas pu être envoyé."""


def send_mail(subject: str, html_body: str, recipients: list[str], text_body: str = "") -> None:
    """Envoie un e-mail HTML aux destinataires (lève MailError en cas d'échec)."""
    if not recipients:
        raise MailError("Aucun destinataire")
    if not settings.mail_configured:
        raise MailError("L'envoi d'e-mails n'est pas configuré (MAIL_BACKEND, MAIL_FROM...)")

    if settings.mail_backend == "graph":
        from app.services.graph_service import GraphMailError, GraphService

        try:
            GraphService().send_mail(settings.mail_from, recipients, subject, html_body)
        except GraphMailError as exc:
            raise MailError(str(exc)) from exc
        return

    _send_smtp(subject, html_body, recipients, text_body)


def _send_smtp(subject: str, html_body: str, recipients: list[str], text_body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.mail_from
    message["To"] = ", ".join(recipients)
    message.set_content(text_body or "Ce message est au format HTML.")
    message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    try:
        if settings.smtp_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30, context=context)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
        with server:
            if settings.smtp_starttls and not settings.smtp_ssl:
                server.starttls(context=context)
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Échec d'envoi SMTP : %s", exc)
        raise MailError("Échec de l'envoi SMTP (voir les journaux du serveur)") from exc
