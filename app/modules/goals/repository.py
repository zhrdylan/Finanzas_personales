"""Repositorio del módulo goals: acceso a datos de metas de ahorro.

Todas las consultas filtran SIEMPRE por ``usuario_id`` (aislamiento por
usuario / prevención de IDOR a nivel de datos).
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals.models import Meta


async def listar_por_usuario(db: AsyncSession, usuario_id: int) -> list[Meta]:
    """Lista las metas del usuario (más recientes primero)."""
    return list(
        (
            await db.scalars(
                select(Meta)
                .where(Meta.usuario_id == usuario_id)
                .order_by(Meta.creado.desc(), Meta.id.desc())
            )
        ).all()
    )


async def obtener_propia(db: AsyncSession, usuario_id: int, meta_id: int) -> Meta | None:
    """Busca una meta por id SOLO dentro del usuario indicado."""
    return await db.scalar(
        select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id,
        )
    )


async def crear(
    db: AsyncSession,
    usuario_id: int,
    *,
    nombre: str,
    monto_objetivo: Decimal,
    monto_inicial: Decimal,
    moneda: str = "COP",
    fecha_limite=None,
) -> Meta:
    """Persiste una meta nueva."""
    meta = Meta(
        usuario_id=usuario_id,
        nombre=nombre,
        monto_objetivo=monto_objetivo,
        monto_actual=monto_inicial,
        moneda=moneda,
        fecha_limite=fecha_limite,
    )
    db.add(meta)
    await db.flush()
    return meta


async def eliminar(db: AsyncSession, meta: Meta) -> None:
    """Elimina la meta indicada."""
    await db.delete(meta)
