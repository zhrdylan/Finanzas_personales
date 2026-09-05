"""Router del módulo transactions: CRUD de movimientos (delgado, sin lógica)."""

from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.categories.schemas import TipoMovimiento
from app.modules.transactions import service
from app.modules.transactions.models import Transaction
from app.modules.transactions.schemas import (
    DireccionOrden,
    MetodoPago,
    MovimientoCreate,
    MovimientoOut,
    MovimientoUpdate,
    OrdenMovimientos,
    PaginaMovimientos,
)
from app.shared.moneda import Moneda

router = APIRouter(prefix="/movimientos", tags=["movimientos"])


@router.get("", response_model=PaginaMovimientos, summary="Listar movimientos")
async def listar(
    usuario: UsuarioActual,
    db: DB,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    metodo_pago: MetodoPago | None = None,
    moneda: Moneda | None = Query(default=None, description="Moneda original"),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    orden: OrdenMovimientos = Query(default="fecha", description="Campo de orden"),
    direccion: DireccionOrden = Query(default="desc", description="Dirección del orden"),
):
    """Lista paginada de los movimientos del usuario con filtros opcionales."""
    return await service.listar(
        db,
        usuario.id,
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


@router.post(
    "",
    response_model=MovimientoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar movimiento",
)
async def crear(datos: MovimientoCreate, usuario: UsuarioActual, db: DB) -> Transaction:
    """Registra un ingreso o gasto asociado al usuario autenticado."""
    return await service.crear(db, usuario.id, datos)


@router.get("/{movimiento_id}", response_model=MovimientoOut, summary="Ver movimiento")
async def obtener(movimiento_id: int, usuario: UsuarioActual, db: DB) -> Transaction:
    """Devuelve un movimiento propio por id."""
    return await service.obtener(db, usuario.id, movimiento_id)


@router.patch("/{movimiento_id}", response_model=MovimientoOut, summary="Editar movimiento")
async def actualizar(
    movimiento_id: int,
    datos: MovimientoUpdate,
    usuario: UsuarioActual,
    db: DB,
) -> Transaction:
    """Actualiza parcialmente un movimiento propio."""
    return await service.actualizar(db, usuario.id, movimiento_id, datos)


@router.delete(
    "/{movimiento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar movimiento",
)
async def eliminar(movimiento_id: int, usuario: UsuarioActual, db: DB) -> None:
    """Elimina un movimiento propio."""
    await service.eliminar(db, usuario.id, movimiento_id)
