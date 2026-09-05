"""Repositorio del módulo categories: acceso a datos de categorías.

Todas las consultas filtran SIEMPRE por ``usuario_id`` (aislamiento por
usuario / prevención de IDOR a nivel de datos).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories.models import Category
from app.modules.transactions.models import Transaction


async def listar_por_usuario(db: AsyncSession, usuario_id: int) -> list[Category]:
    """Lista las categorías del usuario (ingresos y gastos)."""
    return list(
        (
            await db.scalars(
                select(Category)
                .where(Category.usuario_id == usuario_id)
                .order_by(Category.tipo, Category.nombre)
            )
        ).all()
    )


async def obtener_propia(db: AsyncSession, usuario_id: int, categoria_id: int) -> Category | None:
    """Busca una categoría por id SOLO dentro del usuario indicado."""
    return await db.scalar(
        select(Category).where(
            Category.id == categoria_id,
            Category.usuario_id == usuario_id,
        )
    )


async def buscar_duplicada(
    db: AsyncSession,
    usuario_id: int,
    nombre: str,
    tipo: str,
    excluir_id: int | None = None,
) -> Category | None:
    """Busca otra categoría del usuario con mismo nombre y tipo."""
    condiciones = [
        Category.usuario_id == usuario_id,
        Category.nombre == nombre,
        Category.tipo == tipo,
    ]
    if excluir_id is not None:
        condiciones.append(Category.id != excluir_id)
    return await db.scalar(select(Category).where(*condiciones))


async def contar_movimientos(db: AsyncSession, categoria_id: int) -> int:
    """Número de movimientos asociados a la categoría."""
    return (
        await db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.categoria_id == categoria_id)
        )
        or 0
    )


async def crear(db: AsyncSession, usuario_id: int, datos: dict) -> Category:
    """Persiste una categoría nueva."""
    categoria = Category(usuario_id=usuario_id, **datos)
    db.add(categoria)
    await db.flush()
    return categoria


async def eliminar(db: AsyncSession, categoria: Category) -> None:
    """Elimina la categoría indicada."""
    await db.delete(categoria)
