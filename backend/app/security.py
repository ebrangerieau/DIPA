"""
Primitives de sécurité : hachage des mots de passe (bcrypt) et jetons signés (JWT).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import bcrypt
import jwt

from app.config import settings

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_BYTES = 72  # Limite de l'algorithme bcrypt

# Empreintes SHA-256 de mots de passe publiés (exemples de documentation et ancien
# écran de connexion du dépôt public) : refusés et signalés à la connexion.
_COMPROMISED_PASSWORD_SHA256 = frozenset({
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # gitleaks:allow
    "d8f19b426f6fc79f220afcf57681f31b685419ee6da0e4e8a406adb47b6d1c98",  # gitleaks:allow
    "db735458867474ed3163fd668a7324d4c03853bec77d1ab3dc2f070ad92d80dc",  # gitleaks:allow
})


class TokenError(Exception):
    """Jeton absent, expiré, altéré ou d'un type inattendu."""


# ---------- Mots de passe ----------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        # Hash illisible ou mot de passe > 72 octets
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_hex(16))


def burn_password_check() -> None:
    """Effectue une vérification factice pour lisser le temps de réponse (anti-énumération)."""
    verify_password("invalid-password", _dummy_hash())


def is_compromised_password(password: str) -> bool:
    return hashlib.sha256(password.encode("utf-8")).hexdigest() in _COMPROMISED_PASSWORD_SHA256


def password_policy_error(password: str) -> Optional[str]:
    """Retourne un message d'erreur si le mot de passe ne respecte pas la politique, sinon None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"Le mot de passe est trop long ({MAX_PASSWORD_BYTES} octets maximum)."
    if is_compromised_password(password):
        return "Ce mot de passe est connu publiquement : choisissez-en un autre."
    return None


# ---------- Jetons signés ----------

def encode_signed(data: dict, token_type: str, ttl: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {**data, "typ": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_signed(token: str, token_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["exp", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Jeton invalide ou expiré") from exc
    if payload.get("typ") != token_type:
        raise TokenError("Type de jeton inattendu")
    return payload


def create_access_token(user) -> str:
    """Jeton de session : identifiant utilisateur + version (révocation des sessions)."""
    return encode_signed(
        {"sub": str(user.id), "ver": user.token_version or 0},
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
    )
