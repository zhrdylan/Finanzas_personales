"""Repositorio del módulo auth: persistencia de refresh tokens y sesiones."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.modules.auth.models import RefreshToken


async def guardar_refresh(db: AsyncSession, usuario_id: int, token_hash: str, expira) -> None:
    """Registra el hash de un refresh token recién emitido."""
    db.add(RefreshToken(usuario_id=usuario_id, token_hash=token_hash, expira=expira))
    await db.flush()


async def buscar_por_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Busca un refresh token por su hash SHA-256."""
    return await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))


async def revocar(db: AsyncSession, registro: RefreshToken) -> None:
    """Revoca un refresh token (idempotente)."""
    if registro.revocado is None:
        registro.revocado = utcnow()


async def revocar_todos(db: AsyncSession, usuario_id: int) -> None:
    """Revoca TODOS los refresh tokens activos de un usuario."""
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.usuario_id == usuario_id,
            RefreshToken.revocado.is_(None),
        )
        .values(revocado=utcnow())
    )
