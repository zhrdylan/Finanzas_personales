"""Servicio del módulo users: reglas de negocio del perfil y preferencias."""

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.security import hash_password, verify_password
from app.modules.auth.models import RefreshToken
from app.modules.users import repository
from app.modules.users.models import Preferencia, User
from app.modules.users.schemas import (
    PasswordChange,
    PreferenciasUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.shared.exceptions import Conflicto, EntradaInvalida


def a_out(usuario: User, moneda: str) -> UserOut:
    """Construye la representación pública del usuario con su moneda."""
    datos = UserOut.model_validate(usuario)
    return datos.model_copy(update={"moneda": moneda})


async def registrar(db: AsyncSession, datos: UserCreate) -> User:
    """Crea una cuenta nueva (validando unicidad de username/correo)."""
    if await repository.existe_usuario_o_email(db, datos.username, datos.email):
        raise Conflicto("El usuario o el correo ya están registrados")
    return await repository.crear(
        db,
        username=datos.username,
        email=datos.email,
        nombre_completo=datos.nombre_completo,
        hashed_password=hash_password(datos.password),
    )


async def actualizar_perfil(db: AsyncSession, usuario: User, datos: UserUpdate) -> User:
    """Actualiza campos del perfil del usuario autenticado."""
    cambios = datos.model_dump(exclude_unset=True)
    if "nombre_completo" in cambios and cambios["nombre_completo"] is not None:
        usuario.nombre_completo = cambios["nombre_completo"]
        await db.flush()
    return usuario


async def cambiar_password(db: AsyncSession, usuario: User, datos: PasswordChange) -> None:
    """Cambia la contraseña y revoca todas las sesiones activas."""
    if usuario.hashed_password is None:
        # Cuenta creada solo con Google: no hay contraseña actual que pedir.
        # (Entrar por /auth/google y luego definir una es un flujo futuro.)
        raise EntradaInvalida("Tu cuenta usa inicio de sesión con Google y no tiene contraseña")
    if not verify_password(datos.password_actual, usuario.hashed_password):
        raise EntradaInvalida("La contraseña actual no es correcta")
    if verify_password(datos.password_nueva, usuario.hashed_password):
        raise EntradaInvalida("La nueva contraseña debe ser diferente a la actual")

    usuario.hashed_password = hash_password(datos.password_nueva)

    # Seguridad: al cambiar la contraseña se revocan todas las sesiones
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.usuario_id == usuario.id,
            RefreshToken.revocado.is_(None),
        )
        .values(revocado=utcnow())
    )


async def obtener_preferencias(db: AsyncSession, usuario: User) -> Preferencia:
    """Preferencias actuales del usuario (moneda de visualización)."""
    return await repository.obtener_preferencia(db, usuario.id)


async def actualizar_preferencias(
    db: AsyncSession, usuario: User, datos: PreferenciasUpdate
) -> Preferencia:
    """Actualiza la moneda de visualización del usuario (persistencia en BD)."""
    preferencia = await repository.obtener_preferencia(db, usuario.id)
    preferencia.moneda = datos.moneda
    await db.flush()
    return preferencia


def fecha_preferencia(preferencia: Preferencia) -> datetime:
    """Timestamp de última actualización de las preferencias."""
    return preferencia.actualizado
