"""Esquemas Pydantic del módulo goals (metas de ahorro)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.moneda import Moneda

FECHA_MINIMA = date(2000, 1, 1)

# Estados calculados de una meta
EstadoMeta = Literal["activa", "cumplida"]


def _validar_fecha_limite(valor: date | None) -> date | None:
    """La fecha límite debe ser razonable (2000 → +10 años)."""
    if valor is None:
        return valor
    hoy = date.today()
    if valor < FECHA_MINIMA:
        raise ValueError("La fecha límite no puede ser anterior al año 2000")
    if valor > date(hoy.year + 10, hoy.month, hoy.day):
        raise ValueError("La fecha límite no puede ser mayor a 10 años en el futuro")
    return valor


class MetaCreate(BaseModel):
    """Datos para crear una meta de ahorro."""

    nombre: str = Field(min_length=1, max_length=100, examples=["Viaje a Europa"])
    monto_objetivo: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Monto objetivo positivo con hasta 2 decimales",
        examples=[2000000],
    )
    # Ahorro con el que se crea la meta (opcional, por defecto 0)
    monto_inicial: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        max_digits=12,
        decimal_places=2,
        examples=[0],
    )
    fecha_limite: date | None = None
    moneda: Moneda = Field(default="COP", description="Moneda de la meta")

    _v_fecha = field_validator("fecha_limite")(_validar_fecha_limite)

    @field_validator("monto_inicial")
    @classmethod
    def _inicial_menor_que_objetivo(cls, v: Decimal, info):
        objetivo = info.data.get("monto_objetivo")
        if objetivo is not None and v > objetivo:
            raise ValueError("El monto inicial no puede superar el monto objetivo")
        return v


class MetaUpdate(BaseModel):
    """Datos parciales para editar una meta (PATCH)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    monto_objetivo: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    monto_actual: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    moneda: Moneda | None = None
    fecha_limite: date | None = None

    _v_fecha = field_validator("fecha_limite")(_validar_fecha_limite)


class AporteCreate(BaseModel):
    """Aporte de dinero a una meta (registra progreso)."""

    monto: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Monto positivo con hasta 2 decimales",
        examples=[100000],
    )


class MetaOut(BaseModel):
    """Representación pública de una meta con su progreso calculado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    monto_objetivo: Decimal
    monto_actual: Decimal
    moneda: Moneda = "COP"
    fecha_limite: date | None
    # Campos calculados por el servicio (no columnas de la BD)
    porcentaje: float = 0.0
    estado: EstadoMeta = "activa"
    creado: datetime
    actualizado: datetime
