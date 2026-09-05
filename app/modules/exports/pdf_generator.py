"""Generador PDF del módulo exports (ReportLab, en memoria).

Reporte financiero profesional (no una copia de la tabla HTML):
encabezado Flux, resumen en la moneda de visualización, detalle con
montos originales + convertidos, nota de conversión y pie con paginación.
"""

from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.exports.schemas import ReporteExportacion

PIE_TEXTO = "Generado por Flux — Tu dinero, en movimiento"
AZUL = colors.HexColor("#0053ce")
GRIS_OSCURO = colors.HexColor("#0d1843")
GRIS_MEDIO = colors.HexColor("#737686")


def _dinero(valor, moneda: str) -> str:
    """Formatea un importe de forma neutra (Decimal, sin float ni locale)."""
    cuantizado = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{cuantizado:,.2f} {moneda}"


def _pie(canvas, doc) -> None:
    """Pie de página: texto Flux + número de página."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRIS_MEDIO)
    canvas.drawString(15 * mm, 12 * mm, PIE_TEXTO)
    canvas.drawRightString(A4[0] - 15 * mm, 12 * mm, f"Página {doc.page}")
    canvas.restoreState()


def generar_pdf(reporte: ReporteExportacion) -> bytes:
    """Genera el reporte financiero en PDF y lo devuelve como bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Flux — Reporte financiero",
        author="Flux",
        # Sin compresión: el contenido queda inspeccionable (tests) y el
        # reporte sigue siendo liviano para volúmenes personales.
        pageCompression=0,
    )
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("TituloFlux", parent=estilos["Title"], textColor=AZUL, fontSize=22)
    subtitulo = ParagraphStyle(
        "SubFlux", parent=estilos["Normal"], textColor=GRIS_MEDIO, fontSize=10
    )
    h2 = ParagraphStyle("H2Flux", parent=estilos["Heading2"], textColor=GRIS_OSCURO, fontSize=13)
    normal = ParagraphStyle("NormalFlux", parent=estilos["Normal"], fontSize=9, leading=12)
    celda = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=8, leading=10)

    elementos = [
        Paragraph("Flux", titulo),
        Paragraph("Tu dinero, en movimiento", subtitulo),
        Spacer(1, 4 * mm),
        Paragraph("Reporte financiero", h2),
        Spacer(1, 2 * mm),
        Paragraph(f"Usuario: {reporte.usuario} ({reporte.email})", normal),
        Paragraph(
            f"Generado: {reporte.generado.strftime('%Y-%m-%d %H:%M')} · "
            f"Moneda de visualización: {reporte.moneda_visualizacion}",
            normal,
        ),
        Spacer(1, 4 * mm),
        Paragraph("Resumen", h2),
        Spacer(1, 2 * mm),
    ]

    r = reporte.resumen
    tabla_resumen = Table(
        [
            ["Ingresos", _dinero(r.total_ingresos, r.moneda)],
            ["Gastos", _dinero(r.total_gastos, r.moneda)],
            ["Balance", _dinero(r.balance, r.moneda)],
            ["Movimientos", str(r.cantidad_movimientos)],
        ],
        colWidths=[55 * mm, 60 * mm],
    )
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, -1), GRIS_OSCURO),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c2c6d7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos += [tabla_resumen, Spacer(1, 5 * mm), Paragraph("Detalle de movimientos", h2)]

    if not reporte.filas:
        elementos += [
            Spacer(1, 3 * mm),
            Paragraph("Sin movimientos para los filtros indicados.", normal),
        ]
    else:
        encabezado = [
            "Fecha",
            "Tipo",
            "Descripción",
            "Categoría",
            "Original",
            f"En {reporte.moneda_visualizacion}",
        ]
        datos = [encabezado]
        for fila in reporte.filas:
            datos.append(
                [
                    Paragraph(fila.fecha.isoformat(), celda),
                    Paragraph("Ingreso" if fila.tipo == "ingreso" else "Gasto", celda),
                    Paragraph((fila.descripcion or "Movimiento")[:80], celda),
                    Paragraph(fila.categoria[:24], celda),
                    Paragraph(_dinero(fila.monto_original, fila.moneda_original), celda),
                    Paragraph(_dinero(fila.monto_convertido, fila.moneda_visualizacion), celda),
                ]
            )
        tabla = Table(
            datos,
            colWidths=[22 * mm, 18 * mm, 52 * mm, 30 * mm, 28 * mm, 30 * mm],
            repeatRows=1,
        )
        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c2c6d7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f6f8ff")],
                    ),
                ]
            )
        )
        elementos += [Spacer(1, 3 * mm), tabla]

    elementos += [
        Spacer(1, 4 * mm),
        Paragraph("Conversión de moneda", h2),
        Paragraph(
            "Los montos originales se conservan intactos. Los valores en "
            f"{reporte.moneda_visualizacion} usan la tasa histórica de la fecha de "
            "cada movimiento (Frankfurter v2 o caché local).",
            normal,
        ),
    ]

    doc.build(elementos, onFirstPage=_pie, onLaterPages=_pie)
    return buffer.getvalue()
