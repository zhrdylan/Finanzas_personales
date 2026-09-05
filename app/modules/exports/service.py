"""Servicio del módulo exports: arma el reporte y delega la serialización.

Flujo: TransactionsRepository (mismos filtros del listado) →
ExchangeRateService.convert por fila (tasa histórica) → generadores
(Pandas para CSV, ReportLab para PDF). Sin duplicar lógica de conversión
ni de filtros; sin secretos ni datos de otros usuarios (todo filtrado por
el ``usuario_id`` del JWT).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories.schemas import TipoMovimiento
from app.modules.exchange_rates import service as tasas
from app.modules.exports.schemas import FilaExportacion, ReporteExportacion, ResumenExportacion
from app.modules.transactions import repository as movimientos_repo
from app.modules.transactions.schemas import MetodoPago


async def construir_reporte(
    db: AsyncSession,
    *,
    usuario_id: int,
    nombre_usuario: str,
    email: str,
    moneda_visualizacion: str,
    tipo: TipoMovimiento | None = None,
    categoria_id: int | None = None,
    metodo_pago: MetodoPago | None = None,
    moneda: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    q: str | None = None,
) -> ReporteExportacion:
    """Construye el reporte con los filtros indicados (datos reales)."""
    movimientos = await movimientos_repo.listar_todo(
        db,
        usuario_id,
        tipo=tipo,
        categoria_id=categoria_id,
        metodo_pago=metodo_pago,
        moneda=moneda,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        q=q,
    )

    filas: list[FilaExportacion] = []
    ingresos = Decimal("0")
    gastos = Decimal("0")
    for m in movimientos:
        conversion = await tasas.convert(db, m.monto, m.moneda, moneda_visualizacion, m.fecha)
        filas.append(
            FilaExportacion(
                fecha=m.fecha,
                tipo=m.tipo,
                descripcion=m.descripcion or None,
                categoria=m.categoria.nombre if m.categoria else "",
                monto_original=Decimal(str(m.monto)),
                moneda_original=m.moneda,
                moneda_visualizacion=conversion.moneda_destino,
                tasa_cambio=conversion.tasa,
                fecha_tasa_cambio=conversion.fecha_tasa,
                monto_convertido=conversion.monto_convertido,
            )
        )
        if m.tipo == "ingreso":
            ingresos += conversion.monto_convertido
        else:
            gastos += conversion.monto_convertido

    filtros = {
        "tipo": tipo,
        "categoria_id": categoria_id,
        "metodo_pago": metodo_pago,
        "moneda": moneda,
        "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
        "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
        "q": q,
    }
    return ReporteExportacion(
        usuario=nombre_usuario,
        email=email,
        moneda_visualizacion=moneda_visualizacion,  # type: ignore[arg-type]
        generado=datetime.now(),
        filtros=filtros,
        resumen=ResumenExportacion(
            total_ingresos=ingresos,
            total_gastos=gastos,
            balance=ingresos - gastos,
            cantidad_movimientos=len(filas),
            moneda=moneda_visualizacion,  # type: ignore[arg-type]
        ),
        filas=filas,
    )
