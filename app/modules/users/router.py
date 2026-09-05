"""Router del módulo users: perfil, contraseña y preferencias del usuario."""

from fastapi import APIRouter, status

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.users import service
from app.modules.users.schemas import (
    PasswordChange,
    PreferenciasOut,
    PreferenciasUpdate,
    UserOut,
    UserUpdate,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("/me", response_model=UserOut, summary="Perfil del usuario autenticado")
async def perfil(usuario: UsuarioActual, db: DB) -> UserOut:
    """Devuelve los datos públicos del usuario actual (id tomado del JWT),
    incluida su moneda de visualización configurada."""
    preferencia = await service.obtener_preferencias(db, usuario)
    return service.a_out(usuario, preferencia.moneda)


@router.patch("/me", response_model=UserOut, summary="Actualizar perfil")
async def actualizar_perfil(datos: UserUpdate, usuario: UsuarioActual, db: DB) -> UserOut:
    """Actualiza el nombre completo del usuario autenticado."""
    actualizado = await service.actualizar_perfil(db, usuario, datos)
    preferencia = await service.obtener_preferencias(db, actualizado)
    return service.a_out(actualizado, preferencia.moneda)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar contraseña",
)
async def cambiar_password(datos: PasswordChange, usuario: UsuarioActual, db: DB) -> None:
    """Cambia la contraseña (exige la actual) y cierra todas las sesiones."""
    await service.cambiar_password(db, usuario, datos)


@router.get(
    "/me/preferencias",
    response_model=PreferenciasOut,
    summary="Preferencias de la cuenta",
)
async def preferencias(usuario: UsuarioActual, db: DB) -> PreferenciasOut:
    """Devuelve las preferencias del usuario (moneda de visualización)."""
    preferencia = await service.obtener_preferencias(db, usuario)
    return PreferenciasOut(moneda=preferencia.moneda, actualizado=preferencia.actualizado)


@router.patch(
    "/me/preferencias",
    response_model=PreferenciasOut,
    summary="Actualizar preferencias (moneda)",
)
async def actualizar_preferencias(
    datos: PreferenciasUpdate, usuario: UsuarioActual, db: DB
) -> PreferenciasOut:
    """Actualiza la moneda de visualización (COP | USD | EUR).

    La moneda se persiste en MySQL y NO convierte montos: solo define el
    formato con el que la interfaz muestra los importes.
    """
    preferencia = await service.actualizar_preferencias(db, usuario, datos)
    return PreferenciasOut(moneda=preferencia.moneda, actualizado=preferencia.actualizado)
