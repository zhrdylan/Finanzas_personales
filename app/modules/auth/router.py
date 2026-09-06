"""Router del módulo auth: registro, login (rate limit), refresh y logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.deps import DB
from app.core.rate_limit import limiter
from app.modules.auth import service
from app.modules.auth.dependencies import UsuarioActual
from app.modules.auth.google import verificar_id_token
from app.modules.auth.schemas import GoogleConfigOut, GoogleLoginRequest, RefreshRequest, TokenOut
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


@router.get(
    "/google/config",
    response_model=GoogleConfigOut,
    summary="Config pública del botón de Google",
)
async def google_config() -> GoogleConfigOut:
    """Dice al frontend si el inicio con Google está habilitado y con qué Client ID."""
    client_id = settings.GOOGLE_CLIENT_ID.strip()
    if not client_id:
        return GoogleConfigOut(habilitado=False, client_id=None)
    return GoogleConfigOut(habilitado=True, client_id=client_id)


@router.post(
    "/google",
    response_model=TokenOut,
    summary="Iniciar sesión con Google (ID token GIS)",
)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login_google(
    request: Request,  # noqa: ARG001 - requerido por slowapi (clave del limiter)
    datos: GoogleLoginRequest,
    db: DB,
) -> TokenOut:
    """Verifica el ID token de Google y emite los tokens propios de la app.

    Crea la cuenta si no existe o vincula el `sub` si el correo verificado
    ya estaba registrado. Error siempre genérico (401), sin filtrar la causa.
    """
    claims = verificar_id_token(datos.id_token)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o token inválido. Inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await service.autenticar_con_google(db, claims)


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
