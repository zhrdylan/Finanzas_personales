"""Esquemas Pydantic del módulo analysis (predicción y anomalías)."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

Tendencia = Literal["ascendente", "descendente", "estable"]
Severidad = Literal["moderada", "alta", "critica"]


class PrediccionOut(BaseModel):
    """Predicción del gasto del próximo mes (regresión lineal)."""

    disponible: bool
    mes_predicho: str | None = None  # "2026-09"
    valor_predicho: float | None = None
    meses_analizados: int = 0
    tendencia: Tendencia | None = None
    r2: float | None = None  # calidad del ajuste (0 a 1)
    mensaje: str | None = None


class AnomaliaOut(BaseModel):
    """Movimiento marcado como atípico."""

    id: int
    fecha: date
    descripcion: str | None
    tipo: str
    monto: Decimal
    categoria: str
    metodo_pago: str
    puntuacion: float  # mayor => más anómalo
    severidad: Severidad  # banda sobre el Z modificado (comparable entre métodos)


class AnomaliasOut(BaseModel):
    """Resultado del análisis de anomalías."""

    disponible: bool
    metodo: str | None = None
    umbral: str | None = None
    total_analizados: int = 0
    items: list[AnomaliaOut] = []
    mensaje: str | None = None
