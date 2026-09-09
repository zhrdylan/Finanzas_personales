"""Generador PDF del módulo exports con identidad visual Flux (ReportLab, en memoria).

Reporte financiero profesional con identidad de marca Flux:
- Encabezado institucional con logo transparente, tipografía bold y línea cian (#17B9D7).
- Resumen financiero estilizado con paleta Flux y zebra striping (#F2F6FF).
- Detalle de movimientos con encabezado #2E6FF5, bordes sutiles #E2E8F0 e indicadores #10B185.
- Pie de página con paginación de dos pasadas ("Página X de Y") y texto de marca.
"""

from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.exports.schemas import ReporteExportacion

# =============================================================================
# CONSTANTES DE IDENTIDAD DE MARCA FLUX
# =============================================================================
FLUX_BLUE = colors.HexColor("#2E6FF5")       # Azul principal
FLUX_CYAN = colors.HexColor("#17B9D7")       # Cian / turquesa (acento primario)
FLUX_GREEN = colors.HexColor("#10B185")      # Verde (acento secundario / éxito)
FLUX_DARK = colors.HexColor("#1A1A2E")       # Texto principal (casi negro)
FLUX_MUTED = colors.HexColor("#6B7280")      # Gris texto secundario / metadatos
FLUX_ZEBRA = colors.HexColor("#F2F6FF")      # Fondo de tablas alternas
FLUX_BORDER = colors.HexColor("#E2E8F0")     # Bordes / líneas divisorias sutiles
FLUX_WHITE = colors.white

# Ruta predeterminada del logo de Flux (con fallback relativo al módulo)
LOGO_PATH = Path(__file__).resolve().parents[2] / "static" / "img" / "logo-icon.png"

# Texto estándar de pie de página (mantenido por compatibilidad pública)
PIE_TEXTO = "Generado por Flux — Tu dinero, en movimiento"

# Aliases de compatibilidad con versiones previas
AZUL = FLUX_BLUE
GRIS_OSCURO = FLUX_DARK
GRIS_MEDIO = FLUX_MUTED


# =============================================================================
# FUNCIONES AUXILIARES DE FORMATEO Y ESTILOS
# =============================================================================
def _dinero(valor, moneda: str) -> str:
    """Formatea un importe de forma neutra (Decimal, sin float ni locale)."""
    cuantizado = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{cuantizado:,.2f} {moneda}"


def get_flux_styles() -> dict[str, ParagraphStyle]:
    """Crea y retorna los estilos tipográficos centralizados para reportes Flux."""
    estilos_base = getSampleStyleSheet()

    return {
        "h1": ParagraphStyle(
            "FluxH1",
            parent=estilos_base["Heading1"],
            textColor=FLUX_BLUE,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceAfter=2,
        ),
        "h2": ParagraphStyle(
            "FluxH2",
            parent=estilos_base["Heading2"],
            textColor=FLUX_CYAN,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=4,
            spaceAfter=3,
        ),
        "subtitulo": ParagraphStyle(
            "FluxSub",
            parent=estilos_base["Normal"],
            textColor=FLUX_MUTED,
            fontName="Helvetica",
            fontSize=9,
            leading=13,
        ),
        "normal": ParagraphStyle(
            "FluxNormal",
            parent=estilos_base["Normal"],
            textColor=FLUX_DARK,
            fontName="Helvetica",
            fontSize=9,
            leading=13,
        ),
        "normal_bold": ParagraphStyle(
            "FluxNormalBold",
            parent=estilos_base["Normal"],
            textColor=FLUX_DARK,
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
        ),
        "celda": ParagraphStyle(
            "FluxCelda",
            parent=estilos_base["Normal"],
            textColor=FLUX_DARK,
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        ),
        "celda_header": ParagraphStyle(
            "FluxCeldaHeader",
            parent=estilos_base["Normal"],
            textColor=FLUX_WHITE,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
        "celda_ingreso": ParagraphStyle(
            "FluxCeldaIngreso",
            parent=estilos_base["Normal"],
            textColor=FLUX_GREEN,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
        ),
    }


# =============================================================================
# DIBUJO DE ENCABEZADO Y PIE DE PÁGINA (CANVAS)
# =============================================================================
def _draw_logo(canvas_obj, x: float, y: float, width: float = 2.2 * cm) -> float:
    """Dibuja el isotipo de Flux con soporte de transparencia (mask='auto').

    Retorna el ancho total ocupado (ancho + espaciado) o 0.0 si el archivo no existe.
    """
    if os.path.exists(LOGO_PATH):
        try:
            img = ImageReader(str(LOGO_PATH))
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            height = width * aspect
            canvas_obj.drawImage(
                img,
                x,
                y,
                width=width,
                height=height,
                mask="auto",
                preserveAspectRatio=True,
            )
            return width + 3 * mm
        except Exception:
            return 0.0
    return 0.0


def _draw_header(canvas_obj, width: float, height: float) -> None:
    """Dibuja el encabezado institucional en cada página."""
    x_left = 15 * mm
    x_right = width - 15 * mm

    # Logo a la izquierda (~2.2cm de ancho)
    logo_w = 2.2 * cm
    logo_offset = _draw_logo(canvas_obj, x=x_left, y=height - 24 * mm, width=logo_w)

    # Nombre de marca "Flux"
    canvas_obj.setFont("Helvetica-Bold", 18)
    canvas_obj.setFillColor(FLUX_BLUE)
    canvas_obj.drawString(x_left + logo_offset, height - 17 * mm, "Flux")

    # Identificador de reporte a la derecha
    canvas_obj.setFont("Helvetica-Bold", 9)
    canvas_obj.setFillColor(FLUX_CYAN)
    canvas_obj.drawRightString(x_right, height - 16 * mm, "REPORTE FINANCIERO")

    # Línea divisoria de acento cian (#17B9D7) debajo del header
    canvas_obj.setStrokeColor(FLUX_CYAN)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(x_left, height - 26 * mm, x_right, height - 26 * mm)


def _draw_footer(
    canvas_obj, width: float, height: float, page_num: int, total_pages: int
) -> None:
    """Dibuja el pie de página con paginación 'Página X de Y' y metadatos Flux."""
    x_left = 15 * mm
    x_right = width - 15 * mm

    # Línea divisoria superior del pie en #E2E8F0
    canvas_obj.setStrokeColor(FLUX_BORDER)
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(x_left, 18 * mm, x_right, 18 * mm)

    # Texto a la izquierda
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(FLUX_MUTED)
    canvas_obj.drawString(x_left, 12 * mm, PIE_TEXTO)

    # Paginación a la derecha
    canvas_obj.drawRightString(x_right, 12 * mm, f"Página {page_num} de {total_pages}")


class FluxNumberedCanvas(canvas.Canvas):
    """Canvas de 2 pasadas para estampar encabezado, pie y total de páginas dinámicamente."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        w, h = A4
        _draw_header(self, w, h)
        _draw_footer(self, w, h, self._pageNumber, total_pages)
        self.restoreState()


def _pie(canvas_obj, doc) -> None:
    """Función de pie de página mantenida para compatibilidad pública directa."""
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(FLUX_MUTED)
    canvas_obj.drawString(15 * mm, 12 * mm, PIE_TEXTO)
    canvas_obj.drawRightString(A4[0] - 15 * mm, 12 * mm, f"Página {doc.page}")
    canvas_obj.restoreState()


# =============================================================================
# GENERADOR PRINCIPAL DEL REPORTE PDF
# =============================================================================
def generar_pdf(reporte: ReporteExportacion) -> bytes:
    """Genera el reporte financiero en PDF con marca Flux y lo devuelve como bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=32 * mm,
        bottomMargin=24 * mm,
        title="Flux — Reporte financiero",
        author="Flux",
        # Sin compresión: el contenido queda inspeccionable (tests) y el
        # reporte sigue siendo liviano para volúmenes personales.
        pageCompression=0,
    )

    estilos = get_flux_styles()
    h1 = estilos["h1"]
    h2 = estilos["h2"]
    normal = estilos["normal"]
    subtitulo = estilos["subtitulo"]
    celda = estilos["celda"]
    celda_header = estilos["celda_header"]
    celda_ingreso = estilos["celda_ingreso"]

    # Sección inicial: Título del documento y metadatos del reporte
    elementos = [
        Paragraph("Reporte financiero", h1),
        Spacer(1, 2 * mm),
        Paragraph(f"<b>Usuario:</b> {reporte.usuario} ({reporte.email})", normal),
        Paragraph(
            f"<b>Generado:</b> {reporte.generado.strftime('%Y-%m-%d %H:%M')} · "
            f"<b>Moneda de visualización:</b> {reporte.moneda_visualizacion}",
            subtitulo,
        ),
        Spacer(1, 4 * mm),
        Paragraph("Resumen", h2),
        Spacer(1, 2 * mm),
    ]

    # Tabla de resumen financiero con estilo de marca Flux
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
                ("BACKGROUND", (0, 0), (0, -1), FLUX_ZEBRA),
                ("TEXTCOLOR", (0, 0), (-1, -1), FLUX_DARK),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, FLUX_BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos += [
        tabla_resumen,
        Spacer(1, 5 * mm),
        Paragraph("Detalle de movimientos", h2),
    ]

    # Tabla de detalle de movimientos o mensaje vacío
    if not reporte.filas:
        elementos += [
            Spacer(1, 3 * mm),
            Paragraph("Sin movimientos para los filtros indicados.", subtitulo),
        ]
    else:
        encabezado = [
            Paragraph("<b>Fecha</b>", celda_header),
            Paragraph("<b>Tipo</b>", celda_header),
            Paragraph("<b>Descripción</b>", celda_header),
            Paragraph("<b>Categoría</b>", celda_header),
            Paragraph("<b>Original</b>", celda_header),
            Paragraph(f"<b>En {reporte.moneda_visualizacion}</b>", celda_header),
        ]
        datos = [encabezado]
        for fila in reporte.filas:
            tipo_parrafo = (
                Paragraph("Ingreso", celda_ingreso)
                if fila.tipo == "ingreso"
                else Paragraph("Gasto", celda)
            )
            datos.append(
                [
                    Paragraph(fila.fecha.isoformat(), celda),
                    tipo_parrafo,
                    Paragraph((fila.descripcion or "Movimiento")[:80], celda),
                    Paragraph(fila.categoria[:24], celda),
                    Paragraph(_dinero(fila.monto_original, fila.moneda_original), celda),
                    Paragraph(
                        _dinero(fila.monto_convertido, fila.moneda_visualizacion),
                        celda,
                    ),
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
                    ("BACKGROUND", (0, 0), (-1, 0), FLUX_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), FLUX_WHITE),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, FLUX_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [FLUX_WHITE, FLUX_ZEBRA],
                    ),
                ]
            )
        )
        elementos += [Spacer(1, 3 * mm), tabla]

    # Sección final: Explicación de conversión de moneda
    elementos += [
        Spacer(1, 5 * mm),
        Paragraph("Conversión de moneda", h2),
        Paragraph(
            "Los montos originales se conservan intactos. Los valores en "
            f"{reporte.moneda_visualizacion} usan la tasa histórica de la fecha de "
            "cada movimiento (Frankfurter v2 o caché local).",
            subtitulo,
        ),
    ]

    doc.build(elementos, canvasmaker=FluxNumberedCanvas)
    return buffer.getvalue()
