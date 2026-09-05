"""Esquemas del módulo exports: representación intermedia de la exportación.

`FilaExportacion` es una fila del reporte (movimiento + conversión);
`ReporteExportacion` agrupa filas + resumen + metadatos. Los generadores
CSV/PDF consumen esta estructura; nunca tocan la base de datos.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.shared.moneda import Moneda


class FilaExportacion(BaseModel):
    """Un movimiento con su conversión a la moneda de visualización."""

    model_config = ConfigDict(from_attributes=True)

    fecha: date
    tipo: str
    descripcion: str | None = None
    categoria: str
    monto_original: Decimal
    moneda_original: Moneda
    moneda_visualizacion: Moneda
    tasa_cambio: Decimal
    fecha_tasa_cambio: date
    monto_convertido: Decimal


class ResumenExportacion(BaseModel):
    """Totales del reporte expresados en la moneda de visualización."""

    total_ingresos: Decimal
    total_gastos: Decimal
    balance: Decimal
    cantidad_movimientos: int
    moneda: Moneda


class ReporteExportacion(BaseModel):
    """Reporte completo listo para serializar a CSV o PDF."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    usuario: str
    email: str
    moneda_visualizacion: Moneda
    generado: datetime
    filtros: dict
    resumen: ResumenExportacion
    filas: list[FilaExportacion]
