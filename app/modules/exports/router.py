"""Router del módulo exports: descarga de CSV y PDF (delgado, sin lógica).

El usuario SIEMPRE se toma del JWT: nadie puede exportar datos ajenos.
Los filtros son los mismos del listado de movimientos; la moneda de
visualización usa la preferencia del usuario si no se indica.
"""

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.categories.schemas import TipoMovimiento
from app.modules.exports import service
from app.modules.exports.csv_generator import generar_csv
from app.modules.exports.pdf_generator import generar_pdf
from app.modules.transactions.schemas import MetodoPago
from app.modules.users import service as usuarios
from app.shared.moneda import Moneda

router = APIRouter(prefix="/exports", tags=["exportación"])


async def _reporte(
    usuario: UsuarioActual,
    db: DB,
    tipo: TipoMovimiento | None,
    categoria_id: int | None,
    metodo_pago: MetodoPago | None,
    moneda: Moneda | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
    q: str | None,
    visualizacion: Moneda | None,
):
    """Construye el reporte para el usuario autenticado."""
    destino = visualizacion
    if destino is None:
        preferencia = await usuarios.obtener_preferencias(db, usuario)
        destino = preferencia.moneda
    return await service.construir_reporte(
        db,
        usuario_id=usuario.id,
        nombre_usuario=usuario.nombre_completo or usuario.username,
        email=usuario.email,
        moneda_visualizacion=destino,
        tipo=tipo,
        categoria_id=categoria_id,
        metodo_pago=metodo_pago,
        moneda=moneda,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
    )


def _nombre_archivo(extension: str) -> str:
    """Nombre seguro generado en el backend (sin input del frontend)."""
    return f"flux_movimientos_{date.today().isoformat()}.{extension}"


@router.get("/transactions.csv", summary="Exportar movimientos a CSV")
async def exportar_csv(
    usuario: UsuarioActual,
    db: DB,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    metodo_pago: MetodoPago | None = None,
    moneda: Moneda | None = Query(default=None, description="Moneda original"),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    visualizacion: Moneda | None = Query(default=None, description="Moneda de visualización"),
):
    """CSV de movimientos (Pandas) con los filtros indicados."""
    reporte = await _reporte(
        usuario,
        db,
        tipo,
        categoria_id,
        metodo_pago,
        moneda,
        fecha_desde,
        fecha_hasta,
        q,
        visualizacion,
    )
    contenido = generar_csv(reporte)
    return StreamingResponse(
        iter([contenido]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo("csv")}"'},
    )


@router.get("/transactions.pdf", summary="Exportar movimientos a PDF")
async def exportar_pdf(
    usuario: UsuarioActual,
    db: DB,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = Query(default=None, gt=0),
    metodo_pago: MetodoPago | None = None,
    moneda: Moneda | None = Query(default=None, description="Moneda original"),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    q: str | None = Query(default=None, max_length=100),
    visualizacion: Moneda | None = Query(default=None, description="Moneda de visualización"),
):
    """Reporte financiero en PDF (ReportLab) con los filtros indicados."""
    reporte = await _reporte(
        usuario,
        db,
        tipo,
        categoria_id,
        metodo_pago,
        moneda,
        fecha_desde,
        fecha_hasta,
        q,
        visualizacion,
    )
    contenido = generar_pdf(reporte)
    return StreamingResponse(
        iter([contenido]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_nombre_archivo("pdf")}"'},
    )
