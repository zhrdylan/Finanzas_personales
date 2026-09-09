"""Repositorio del módulo goals: acceso a datos de metas de ahorro.

Todas las consultas filtran SIEMPRE por ``usuario_id`` (aislamiento por
usuario / prevención de IDOR a nivel de datos).
"""

from decimal import Decimal

from sqlalchemy import select, update
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


async def abonar_atomico(
    db: AsyncSession, usuario_id: int, meta_id: int, monto: Decimal
) -> Meta | None:
    """Incrementa ``monto_actual`` de forma atómica a nivel SQL.

    Equivale a ``UPDATE metas SET monto_actual = monto_actual + :monto
    WHERE id = :id AND usuario_id = :usuario_id``: la suma la ejecuta el
    motor en una sola sentencia, por lo que N peticiones concurrentes no
    pueden producir *lost updates*. El filtro por ``usuario_id`` mantiene
    el aislamiento multi-inquilino (recurso ajeno/inexistente → None → 404).

    Se re-lee la fila en la misma transacción (gestionada por ``get_db``)
    para devolver el estado fresco. ``synchronize_session=False`` porque no
    hay instancias ORM que sincronizar: cada petición usa su propia sesión.
    """
    resultado = await db.execute(
        update(Meta)
        .where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id,
        )
        .values(monto_actual=Meta.monto_actual + monto)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount == 0:
        # Ninguna fila coincide: la meta no existe o es de otro usuario.
        # (monto siempre > 0 por validación Pydantic, así que rowcount 0
        #  implica "no encontrada", no "sin cambios").
        return None
    return await db.scalar(
        select(Meta).where(
            Meta.id == meta_id,
            Meta.usuario_id == usuario_id,
        )
    )


async def eliminar(db: AsyncSession, meta: Meta) -> None:
    """Elimina la meta indicada."""
    await db.delete(meta)
