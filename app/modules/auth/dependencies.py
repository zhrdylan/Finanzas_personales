"""Dependencias de autenticación: resolución del usuario actual desde el JWT.

El id de usuario SIEMPRE proviene del token, nunca de la URL ni de un
parámetro de consulta (prevención de IDOR).
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.deps import DB
from app.core.security import decodificar_token
from app.modules.users.models import User

# Esquema de seguridad: el frontend envía "Authorization: Bearer <access_token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

_ERROR_SESION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas o sesión expirada",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DB,
) -> User:
    """Resuelve el usuario autenticado a partir del JWT del encabezado."""
    usuario_id = decodificar_token(token, tipo_esperado="access")
    if usuario_id is None:
        raise _ERROR_SESION

    usuario = await db.get(User, usuario_id)
    if usuario is None or not usuario.is_active:
        raise _ERROR_SESION
    return usuario


# Atajo de anotación para el usuario autenticado
UsuarioActual = Annotated[User, Depends(get_current_user)]
