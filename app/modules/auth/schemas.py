"""Esquemas Pydantic del módulo auth (tokens)."""

from pydantic import BaseModel, Field

from app.modules.users.schemas import UserOut


class RefreshRequest(BaseModel):
    """Cuerpo de /auth/refresh y /auth/logout."""

    refresh_token: str = Field(min_length=20, max_length=512)


class TokenOut(BaseModel):
    """Par de tokens + datos del usuario (respuesta de login/refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - tipo de token OAuth2, no credencial
    usuario: UserOut
