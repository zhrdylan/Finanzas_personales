"""Inicio de sesión con Google (Google Identity Services).

Flujo: el frontend obtiene un ID token con GIS y lo envía a
``POST /auth/google``; aquí solo se VERIFICA su firma contra los
certificados de Google y que fue emitido para nuestro Client ID.
Nunca se acepta un token sin verificar ni se confía en datos del
cliente distintos del propio ID token.
"""

import logging
import re

from app.core.config import settings

logger = logging.getLogger("app.auth.google")

# Emisores válidos de ID tokens de Google (cuentas personales y Workspace).
_EMISORES_GOOGLE = {"accounts.google.com", "https://accounts.google.com"}

# Username: solo letras, números y guion bajo (igual que UserCreate).
_NO_PERMITIDO_USERNAME = re.compile(r"[^a-zA-Z0-9_]+")


def derivar_username_base(email: str) -> str:
    """Propone un username a partir del correo (parte local saneada).

    Función pura (sin BD): la unicidad se resuelve en el servicio
    añadiendo sufijo numérico hasta encontrar uno libre.
    """
    local = email.strip().lower().split("@")[0]
    base = _NO_PERMITIDO_USERNAME.sub("_", local).strip("_")
    if len(base) < 3:
        base = f"usuario_{base}" if base else "usuario_google"
    return base[:40]


def verificar_id_token(id_token: str) -> dict | None:
    """Verifica el ID token de Google y devuelve sus claims.

    Comprueba firma, expiración, emisor y audiencia (nuestro
    ``GOOGLE_CLIENT_ID``). Devuelve ``None`` si algo falla, sin filtrar
    el motivo (el llamador responde 401 genérico).
    """
    if not settings.GOOGLE_CLIENT_ID:
        logger.warning("Intento de login con Google sin GOOGLE_CLIENT_ID configurado.")
        return None
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        claims = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:  # noqa: BLE001 - cualquier fallo => token inválido
        logger.warning("ID token de Google inválido: %s", type(exc).__name__)
        return None
    if claims.get("iss") not in _EMISORES_GOOGLE:
        logger.warning("ID token de Google con emisor inesperado.")
        return None
    if not claims.get("sub") or not claims.get("email"):
        return None
    return claims
