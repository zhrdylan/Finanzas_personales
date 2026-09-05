"""Servicio del módulo transactions: reglas de negocio de movimientos."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories import repository as categorias_repo
from app.modules.categories.schemas import TipoMovimiento
from app.modules.transactions import repository
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import (
    DireccionOrden,
    MetodoPago,
    MovimientoCreate,
    MovimientoUpdate,
    OrdenMovimientos,
)
from app.shared.exceptions import EntradaInvalida, NoEncontrado
from app.shared.pagination import Pagina


async def _validar_categoria(
    db: AsyncSession, usuario_id: int, categoria_id: int, tipo: TipoMovimiento
) -> None:
    """La categoría debe existir, ser del usuario y coincidir en tipo."""
    categoria = await categorias_repo.obtener_propia(db, usuario_id, categoria_id)
    if categoria is None:
        raise NoEncontrado("Categoría no encontrada")
    if categoria.tipo != tipo:
        raise EntradaInvalida("El tipo del movimiento no coincide con el tipo de la categoría")


async def listar(
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
    por_pagina: int = 20,
    orden: OrdenMovimientos = "fecha",
    direccion: DireccionOrden = "desc",
) -> Pagina:
    """Lista paginada de movimientos del usuario autenticado."""
    return await repository.listar_paginado(
        db,
        usuario_id,
        tipo=tipo,
        categoria_id=categoria_id,
        metodo_pago=metodo_pago,
        moneda=moneda,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
        pagina=pagina,
        por_pagina=por_pagina,
        orden=orden,
        direccion=direccion,
    )


async def obtener(db: AsyncSession, usuario_id: int, movimiento_id: int) -> Transaction:
    """Devuelve un movimiento propio (404 si no existe o es ajeno)."""
    movimiento = await repository.obtener_propio(db, usuario_id, movimiento_id)
    if movimiento is None:
        raise NoEncontrado("Movimiento no encontrado")
    return movimiento


def _normalizar_notas(valor: str | None) -> str | None:
    """Normaliza notas: recorta espacios y convierte "" en None."""
    if valor is None:
        return None
    texto = valor.strip()
    return texto or None


async def crear(db: AsyncSession, usuario_id: int, datos: MovimientoCreate) -> Transaction:
    """Registra un ingreso o gasto asociado al usuario autenticado."""
    await _validar_categoria(db, usuario_id, datos.categoria_id, datos.tipo)
    return await repository.crear(
        db,
        usuario_id,
        {
            "categoria_id": datos.categoria_id,
            "tipo": datos.tipo,
            "monto": datos.monto,
            "moneda": datos.moneda,
            "fecha": datos.fecha,
            "descripcion": datos.descripcion or "",
            "notas": _normalizar_notas(datos.notas),
            "metodo_pago": datos.metodo_pago,
        },
    )


async def actualizar(
    db: AsyncSession, usuario_id: int, movimiento_id: int, datos: MovimientoUpdate
) -> Transaction:
    """Actualiza parcialmente un movimiento propio."""
    movimiento = await obtener(db, usuario_id, movimiento_id)
    cambios = datos.model_dump(exclude_unset=True)

    # Consistencia: el tipo final debe seguir coincidiendo con la categoría final
    if {"tipo", "categoria_id"} & cambios.keys():
        tipo_final = cambios.get("tipo", movimiento.tipo)
        categoria_final = cambios.get("categoria_id", movimiento.categoria_id)
        await _validar_categoria(db, usuario_id, categoria_final, tipo_final)

    for campo, valor in cambios.items():
        if campo == "notas":
            setattr(movimiento, campo, _normalizar_notas(valor))
        else:
            setattr(movimiento, campo, valor)
    if cambios.get("descripcion") is None and "descripcion" in cambios:
        movimiento.descripcion = ""

    await db.flush()
    if "categoria_id" in cambios:
        await db.refresh(movimiento, attribute_names=["categoria"])
    return movimiento


async def eliminar(db: AsyncSession, usuario_id: int, movimiento_id: int) -> None:
    """Elimina un movimiento propio."""
    movimiento = await obtener(db, usuario_id, movimiento_id)
    await db.delete(movimiento)
