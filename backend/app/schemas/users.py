"""
Schémas des utilisateurs et de l'authentification.
"""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Validation syntaxique volontairement souple : les comptes locaux internes utilisent
# parfois des domaines réservés (.local) que les validateurs stricts refusent.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=255, pattern=EMAIL_PATTERN)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: Optional[str]
    display_name: str
    is_admin: bool
    is_active: bool
    auth_provider: str
    has_local_password: bool
    must_change_password: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]


class LoginResponse(BaseModel):
    """Réponse de connexion. Le jeton est aussi posé en cookie httpOnly pour l'application web."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AuthConfig(BaseModel):
    app_name: str
    app_version: str
    local_enabled: bool
    sso_enabled: bool


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9._@-]+$")
    email: Email
    full_name: Optional[str] = Field(default=None, max_length=255)
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    email: Optional[Email] = None
    full_name: Optional[str] = Field(default=None, max_length=255)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class PasswordReset(BaseModel):
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
