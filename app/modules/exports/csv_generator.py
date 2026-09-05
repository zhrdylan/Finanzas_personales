"""Generador CSV del módulo exports (Pandas, en memoria).

Columnas: fecha, tipo, descripcion, categoria, monto_original,
moneda_original, moneda_visualizacion, tasa_cambio, fecha_tasa_cambio,
monto_convertido. Sin secretos ni datos ajenos (el reporte ya viene
filtrado por usuario).
"""

import pandas as pd

from app.modules.exports.schemas import ReporteExportacion

COLUMNAS = [
    "fecha",
    "tipo",
    "descripcion",
    "categoria",
    "monto_original",
    "moneda_original",
    "moneda_visualizacion",
    "tasa_cambio",
    "fecha_tasa_cambio",
    "monto_convertido",
]


def generar_csv(reporte: ReporteExportacion) -> bytes:
    """Serializa el reporte a CSV (UTF-8 con BOM para Excel)."""
    registros = [
        {
            "fecha": fila.fecha.isoformat(),
            "tipo": fila.tipo,
            "descripcion": fila.descripcion or "",
            "categoria": fila.categoria,
            "monto_original": str(fila.monto_original),
            "moneda_original": fila.moneda_original,
            "moneda_visualizacion": fila.moneda_visualizacion,
            "tasa_cambio": str(fila.tasa_cambio),
            "fecha_tasa_cambio": fila.fecha_tasa_cambio.isoformat(),
            "monto_convertido": str(fila.monto_convertido),
        }
        for fila in reporte.filas
    ]
    df = pd.DataFrame(registros, columns=COLUMNAS)
    return df.to_csv(index=False).encode("utf-8-sig")
