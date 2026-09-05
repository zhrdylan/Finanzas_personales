"""Repositorio del módulo users: acceso a datos de usuarios y preferencias.

Solo consultas/persistencia; sin lógica de negocio ni de presentación.
"""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import Preferencia, User


async def buscar_por_identificador(db: AsyncSession, identificador: str) -> User | None:
    """Busca un usuario por username O por correo (normalizado a minúsculas)."""
    texto = identificador.strip()
    if "@" in texto:
        texto = texto.lower()
    return await db.scalar(select(User).where(or_(User.username == texto, User.email == texto)))


async def existe_usuario_o_email(db: AsyncSession, username: str, email: str) -> bool:
    """True si ya existe un usuario con ese username o correo."""
    return (
        await db.scalar(select(User.id).where(or_(User.username == username, User.email == email)))
        is not None
    )


async def crear(
    db: AsyncSession, *, username: str, email: str, nombre_completo: str, hashed_password: str
) -> User:
    """Persiste un usuario nuevo (y su fila de preferencias por defecto)."""
    usuario = User(
        username=username,
        email=email,
        nombre_completo=nombre_completo,
        hashed_password=hashed_password,
    )
    db.add(usuario)
    await db.flush()

    # Toda cuenta nace con preferencias por defecto (moneda COP)
    db.add(Preferencia(usuario_id=usuario.id))
    await db.flush()
    return usuario


async def obtener_preferencia(db: AsyncSession, usuario_id: int) -> Preferencia:
    """Devuelve las preferencias del usuario (creándolas si no existen)."""
    preferencia = await db.get(Preferencia, usuario_id)
    if preferencia is None:
        # Fallback para cuentas anteriores a la migración 0002
        preferencia = Preferencia(usuario_id=usuario_id)
        db.add(preferencia)
        await db.flush()
    return preferencia
