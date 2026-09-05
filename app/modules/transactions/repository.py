"""Repositorio del módulo transactions: acceso a datos de movimientos.

Todas las consultas filtran SIEMPRE por ``usuario_id`` (aislamiento por
usuario / prevención de IDOR a nivel de datos).
"""

import math
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.categories.schemas import TipoMovimiento
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import DireccionOrden, MetodoPago, OrdenMovimientos
from app.shared.pagination import Pagina

POR_PAGINA_DEFECTO = 20


def ordenar_movimientos(orden: OrdenMovimientos, direccion: DireccionOrden):
    """Cláusulas ORDER BY del listado (whitelist, sin texto concatenado).

    El id como desempate mantiene el orden estable entre páginas.
    """
    descendente = direccion == "desc"
    if orden == "monto":
        principal = Transaction.monto.desc() if descendente else Transaction.monto.asc()
    else:
        principal = Transaction.fecha.desc() if descendente else Transaction.fecha.asc()
    desempate = Transaction.id.desc() if descendente else Transaction.id.asc()
    return [principal, desempate]


def aplicar_filtros(
    stmt: Select,
    usuario_id: int,
    tipo: TipoMovimiento | None,
    categoria_id: int | None,
    metodo_pago: MetodoPago | None,
    moneda: str | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    q: str | None,
) -> Select:
    """Encadena filtros dinámicos a la consulta (todos parametrizados)."""
    condiciones = [Transaction.usuario_id == usuario_id]
    if tipo:
        condiciones.append(Transaction.tipo == tipo)
    if categoria_id:
        condiciones.append(Transaction.categoria_id == categoria_id)
    if metodo_pago:
        condiciones.append(Transaction.metodo_pago == metodo_pago)
    if moneda:
        condiciones.append(Transaction.moneda == moneda)
    if fecha_desde:
        condiciones.append(Transaction.fecha >= fecha_desde)
    if fecha_hasta:
        condiciones.append(Transaction.fecha <= fecha_hasta)
    if q:
        # LIKE con parámetro enlazado: seguro ante inyección SQL.
        # Busca en concepto (descripcion) y en notas adicionales.
        patron = f"%{q}%"
        condiciones.append(
            or_(
                Transaction.descripcion.ilike(patron),
                Transaction.notas.ilike(patron),
            )
        )
    return stmt.where(*condiciones)


async def listar_paginado(
    db: AsyncSession,
    usuario_id: int,
    *,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = None,
    metodo_pago: MetodoPago | None = None,
    moneda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    q: str | None = None,
    pagina: int = 1,
    por_pagina: int = POR_PAGINA_DEFECTO,
    orden: OrdenMovimientos = "fecha",
    direccion: DireccionOrden = "desc",
) -> Pagina:
    """Lista paginada de movimientos del usuario con filtros opcionales."""
    base = aplicar_filtros(
        select(Transaction),
        usuario_id,
        tipo,
        categoria_id,
        metodo_pago,
        moneda,
        fecha_desde,
        fecha_hasta,
        q,
    )

    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0

    items = list(
        (
            await db.scalars(
                base.options(selectinload(Transaction.categoria))
                .order_by(*ordenar_movimientos(orden, direccion))
                .offset((pagina - 1) * por_pagina)
                .limit(por_pagina)
            )
        ).all()
    )

    return Pagina(
        items=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=max(1, math.ceil(total / por_pagina)),
    )


async def listar_todo(
    db: AsyncSession,
    usuario_id: int,
    *,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = None,
    metodo_pago: MetodoPago | None = None,
    moneda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    q: str | None = None,
) -> list[Transaction]:
    """Todos los movimientos del usuario que cumplen los filtros (sin paginar).

    Se usa para exportaciones: respeta exactamente los mismos filtros del
    listado. Ordenados por fecha descendente.
    """
    base = aplicar_filtros(
        select(Transaction),
        usuario_id,
        tipo,
        categoria_id,
        metodo_pago,
        moneda,
        fecha_desde,
        fecha_hasta,
        q,
    )
    return list(
        (
            await db.scalars(
                base.options(selectinload(Transaction.categoria)).order_by(
                    Transaction.fecha.desc(), Transaction.id.desc()
                )
            )
        ).all()
    )


async def obtener_propio(
    db: AsyncSession, usuario_id: int, movimiento_id: int
) -> Transaction | None:
    """Busca un movimiento por id SOLO si pertenece al usuario (anti-IDOR)."""
    return await db.scalar(
        select(Transaction)
        .where(
            Transaction.id == movimiento_id,
            Transaction.usuario_id == usuario_id,
        )
        .options(selectinload(Transaction.categoria))
    )


async def crear(db: AsyncSession, usuario_id: int, datos: dict) -> Transaction:
    """Persiste un movimiento nuevo."""
    movimiento = Transaction(usuario_id=usuario_id, **datos)
    db.add(movimiento)
    await db.flush()
    await db.refresh(movimiento, attribute_names=["categoria"])
    return movimiento
