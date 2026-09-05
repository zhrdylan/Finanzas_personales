"""Esquemas Pydantic del módulo users (perfil, contraseña y preferencias)."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.shared.moneda import Moneda

# Patrón seguro para nombre de usuario: letras, números y guion bajo
PATRON_USERNAME = re.compile(r"^[a-zA-Z0-9_]+$")


def _validar_password(valor: str) -> str:
    """Regla de contraseña: al menos una letra y un número."""
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("La contraseña debe incluir al menos una letra y un número")
    return valor


class UserBase(BaseModel):
    """Campos comunes del usuario."""

    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Letras, números y guion bajo",
        examples=["ana"],
    )
    email: EmailStr
    nombre_completo: str = Field(min_length=2, max_length=100, examples=["Ana García"])

    @field_validator("email", mode="before")
    @classmethod
    def _email_minusculas(cls, valor: str) -> str:
        # Normaliza el correo a minúsculas (evita duplicados por capitalización)
        return valor.strip().lower() if isinstance(valor, str) else valor


class UserCreate(UserBase):
    """Datos para registrar un usuario."""

    # bcrypt solo procesa 72 bytes: se limita la longitud
    password: str = Field(min_length=8, max_length=72, description="Mínimo 8 caracteres")

    _v_password = field_validator("password")(_validar_password)


class UserUpdate(BaseModel):
    """Datos actualizables del perfil."""

    nombre_completo: str | None = Field(default=None, min_length=2, max_length=100)


class PasswordChange(BaseModel):
    """Cambio de contraseña (requiere la actual)."""

    password_actual: str = Field(min_length=1, max_length=72)
    password_nueva: str = Field(min_length=8, max_length=72)

    _v_nueva = field_validator("password_nueva")(_validar_password)


class PreferenciasUpdate(BaseModel):
    """Actualización de preferencias (hoy: moneda de visualización)."""

    moneda: Moneda


class PreferenciasOut(BaseModel):
    """Preferencias del usuario autenticado."""

    moneda: Moneda
    actualizado: datetime


class UserOut(BaseModel):
    """Representación pública del usuario (sin datos sensibles)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    nombre_completo: str
    fecha_registro: datetime
    # Moneda de visualización (denormalizada desde preferencias para comodidad)
    moneda: Moneda = "COP"
