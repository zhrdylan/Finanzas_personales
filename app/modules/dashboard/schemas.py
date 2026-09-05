"""Esquemas Pydantic del módulo dashboard (resumen y gráficos del panel)."""

from decimal import Decimal

from pydantic import BaseModel

from app.modules.analysis.schemas import AnomaliasOut, PrediccionOut
from app.shared.moneda import Moneda

# Reexporta para la firma de los endpoints del panel
__all__ = [
    "ResumenOut",
    "CategoriaGastoOut",
    "EvolucionOut",
    "PrediccionOut",
    "AnomaliasOut",
    "PanelCompletoOut",
]


class ResumenOut(BaseModel):
    """Totales de un mes: ingresos, gastos y balance (en ``moneda``)."""

    mes: str  # "2026-08"
    total_ingresos: Decimal
    total_gastos: Decimal
    balance: Decimal
    cantidad_movimientos: int
    moneda: Moneda = "COP"


class CategoriaGastoOut(BaseModel):
    """Un tramo del gráfico de dona (gastos de una categoría)."""

    categoria_id: int
    nombre: str
    color: str
    total: Decimal
    porcentaje: float


class EvolucionOut(BaseModel):
    """Serie de los últimos 6 meses (etiquetas 'YYYY-MM')."""

    meses: list[str]
    ingresos: list[Decimal]
    gastos: list[Decimal]


class PanelCompletoOut(BaseModel):
    """Vista combinada del panel: resumen + evolución + predicción + anomalías.

    Reduce el número de peticiones del frontend sin sacrificar los
    endpoints individuales (que siguen disponibles).
    """

    resumen: ResumenOut
    gastos_por_categoria: list[CategoriaGastoOut]
    evolucion: EvolucionOut
    prediccion: PrediccionOut
    anomalias: AnomaliasOut
    moneda: Moneda = "COP"
