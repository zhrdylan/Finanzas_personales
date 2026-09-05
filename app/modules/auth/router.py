"""Router del módulo auth: registro, login (rate limit), refresh y logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import DB
from app.core.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.dependencies import UsuarioActual
from app.modules.auth.schemas import RefreshRequest, TokenOut
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post(
    "/registro",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
)
async def registro(datos: UserCreate, db: DB) -> User:
    """Crea una cuenta nueva; la contraseña se almacena hasheada con bcrypt."""
    return await service.registrar(db, datos)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Iniciar sesión (OAuth2 password flow)",
)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(
    request: Request,  # noqa: ARG001 - requerido por slowapi (clave del limiter)
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DB,
) -> TokenOut:
    """Autentica con usuario o correo + contraseña.

    Limitado a 5 intentos por minuto e IP (freno a fuerza bruta, configurable
    con LOGIN_RATE_LIMIT). El mensaje de error es genérico: no revela si
    falló el usuario o la contraseña.
    """
    return await service.autenticar(db, form.username, form.password)


@router.post("/refresh", response_model=TokenOut, summary="Renovar tokens (rotación)")
async def refresh(datos: RefreshRequest, db: DB) -> TokenOut:
    """Intercambia un refresh token válido por un par nuevo (rotación de un solo uso)."""
    return await service.renovar(db, datos)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión (revoca el refresh token)",
)
async def logout(
    datos: RefreshRequest,
    usuario: UsuarioActual,
    db: DB,
) -> None:
    """Revoca el refresh token indicado (idempotente). El access token
    expira solo, por diseño, en pocos minutos."""
    await service.cerrar_sesion(db, usuario, datos)


@router.post(
    "/logout-todos",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión en todos los dispositivos",
)
async def logout_todos(usuario: UsuarioActual, db: DB) -> None:
    """Revoca TODOS los refresh tokens activos del usuario autenticado."""
    await service.cerrar_sesion_en_todos(db, usuario)
