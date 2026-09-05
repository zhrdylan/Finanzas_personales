"""Esquemas Pydantic del módulo transactions (movimientos)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.categories.schemas import CategoriaOut, TipoMovimiento
from app.shared.moneda import Moneda
from app.shared.pagination import Pagina

MetodoPago = Literal["efectivo", "tarjeta", "transferencia", "otro"]

# Orden del listado (whitelist: nunca se concatena texto en el ORDER BY)
OrdenMovimientos = Literal["fecha", "monto"]
DireccionOrden = Literal["asc", "desc"]

FECHA_MINIMA = date(2000, 1, 1)


def _validar_fecha(valor: date) -> date:
    """La fecha debe ser razonable: ni antigua ni demasiado futura."""
    hoy = date.today()
    if valor < FECHA_MINIMA:
        raise ValueError("La fecha no puede ser anterior al año 2000")
    if valor > date(hoy.year + 1, hoy.month, hoy.day):
        raise ValueError("La fecha no puede ser mayor a un año en el futuro")
    return valor


class MovimientoBase(BaseModel):
    """Campos comunes de un movimiento."""

    tipo: TipoMovimiento
    monto: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Monto positivo con hasta 2 decimales",
        examples=[45000.50],
    )
    categoria_id: int = Field(gt=0)
    fecha: date
    moneda: Moneda = Field(default="COP", description="Moneda original del registro")
    descripcion: str | None = Field(
        default=None, max_length=255, description="Concepto del movimiento"
    )
    notas: str | None = Field(
        default=None, max_length=500, description="Notas adicionales opcionales"
    )
    metodo_pago: MetodoPago

    _v_fecha = field_validator("fecha")(_validar_fecha)


class MovimientoCreate(MovimientoBase):
    """Datos para registrar un movimiento."""


class MovimientoUpdate(BaseModel):
    """Datos parciales para editar un movimiento (PATCH)."""

    tipo: TipoMovimiento | None = None
    monto: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    categoria_id: int | None = Field(default=None, gt=0)
    fecha: date | None = None
    moneda: Moneda | None = None
    descripcion: str | None = Field(default=None, max_length=255)
    notas: str | None = Field(default=None, max_length=500)
    metodo_pago: MetodoPago | None = None

    _v_fecha = field_validator("fecha")(_validar_fecha)


class MovimientoOut(BaseModel):
    """Representación pública de un movimiento (incluye su categoría)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoMovimiento
    monto: Decimal
    moneda: Moneda = "COP"
    fecha: date
    descripcion: str | None
    notas: str | None = None
    metodo_pago: MetodoPago
    categoria: CategoriaOut
    creado: datetime


# Respuesta paginada de movimientos
PaginaMovimientos = Pagina[MovimientoOut]
