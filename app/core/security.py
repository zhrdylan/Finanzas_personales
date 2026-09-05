"""Utilidades de seguridad: hash de contraseñas (bcrypt) y tokens JWT.

Convenciones del proyecto:
- La contraseña NUNCA se almacena en texto plano, solo su hash bcrypt.
- El hash se hace con la librería ``bcrypt`` directamente (sin passlib):
  menos dependencias y compatibilidad garantizada con bcrypt 5.x. El
  formato ``$2b$`` es idéntico al que generaba passlib, por lo que los
  hashes existentes siguen siendo válidos.
- Access token: vida corta (30 min por defecto).
- Refresh token: vida larga (7 días), se guarda su hash SHA-256 en la BD
  para poder revocarlo (logout) y rotarlo en cada renovación.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Literal

import bcrypt
import jwt  # PyJWT

from app.core.config import settings
from app.core.database import utcnow

# 12 rondas: ~250 ms por hash en hardware moderno (buen equilibrio)
_RONDAS_BCRYPT = 12

TipoToken = Literal["access", "refresh"]


# --------------------------------------------------------------------------- #
# Contraseñas
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de la contraseña (con sal aleatoria)."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_RONDAS_BCRYPT))
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Compara una contraseña en claro contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash corrupto o formato inválido: fallo cerrado.
        return False


# --------------------------------------------------------------------------- #
# Tokens JWT
# --------------------------------------------------------------------------- #
def _crear_token(usuario_id: int, tipo: TipoToken, vida: timedelta) -> str:
    """Firma un JWT con: subject (id de usuario), tipo, emisión y expiración.

    El claim ``jti`` (JWT ID) garantiza que dos tokens emitidos en el mismo
    segundo sean distintos: sin él, logins repetidos colisionarían en el
    índice único de ``refresh_tokens.token_hash``.
    """
    ahora = utcnow()
    payload = {
        "sub": str(usuario_id),  # 'sub' debe ser string (estándar JWT)
        "type": tipo,
        "iat": ahora,
        "exp": ahora + vida,
        "iss": settings.APP_NAME,
        "jti": secrets.token_hex(16),  # identificador único del token
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def crear_access_token(usuario_id: int) -> str:
    """Token de acceso de vida corta."""
    return _crear_token(
        usuario_id, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )


def crear_refresh_token(usuario_id: int) -> tuple[str, datetime]:
    """Token de renovación; devuelve (JWT crudo, fecha de expiración)."""
    expiracion = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = _crear_token(usuario_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    return token, expiracion


def decodificar_token(token: str, tipo_esperado: TipoToken) -> int | None:
    """Decodifica y valida un JWT.

    Devuelve el id de usuario si el token es válido, no ha expirado y es del
    tipo esperado; ``None`` en cualquier otro caso (sin filtrar detalles del
    motivo, para no dar pistas a un atacante).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != tipo_esperado:
            return None
        sub = payload.get("sub")
        return int(sub) if sub is not None else None
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- #
# Utilidades para refresh tokens (almacenados hasheados en la BD)
# --------------------------------------------------------------------------- #
def hash_token(token: str) -> str:
    """Hash SHA-256 del refresh token (nunca se guarda el token crudo)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generar_token_opaco() -> str:
    """Cadena aleatoria criptográficamente segura (usos internos)."""
    return secrets.token_urlsafe(48)
