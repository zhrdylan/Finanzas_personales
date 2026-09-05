"""Esquemas Pydantic del módulo exchange_rates."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.shared.moneda import Moneda

OrigenTasa = Literal["cache", "proveedor", "fallback"]


class TasaOut(BaseModel):
    """Tasa base → quote con su fecha y origen (caché, proveedor o fallback)."""

    model_config = ConfigDict(from_attributes=True)

    base: Moneda
    quote: Moneda
    rate: Decimal
    rate_date: date
    origen: OrigenTasa


class ConversionOut(BaseModel):
    """Resultado de convertir un importe (el original nunca se modifica)."""

    monto_original: Decimal
    moneda_original: Moneda
    monto_convertido: Decimal
    moneda_destino: Moneda
    tasa: Decimal
    fecha_tasa: date
    origen_tasa: OrigenTasa
