"""Router del módulo dashboard: panel financiero (resumen y gráficos).

Router delgado: la lógica de cálculo vive en los servicios. El usuario
SIEMPRE se toma del JWT; el parámetro ``mes`` es solo un rango de consulta.
"""

from fastapi import APIRouter, Query

from app.core.deps import DB
from app.modules.analysis import service as analysis
from app.modules.analysis.schemas import AnomaliasOut, PrediccionOut
from app.modules.auth.dependencies import UsuarioActual
from app.modules.dashboard import service
from app.modules.dashboard.schemas import (
    CategoriaGastoOut,
    EvolucionOut,
    PanelCompletoOut,
    ResumenOut,
)
from app.modules.users import service as usuarios
from app.shared.moneda import Moneda

router = APIRouter(prefix="/panel", tags=["panel y análisis"])

PATRON_MES = r"^\d{4}-(0[1-9]|1[0-2])$"


def _descomponer_mes(mes: str) -> tuple[int, int]:
    """'2026-08' -> (2026, 8). El patrón ya garantiza el formato."""
    return int(mes[:4]), int(mes[5:7])


async def _moneda_vista(db: DB, usuario: UsuarioActual, moneda: Moneda | None) -> str:
    """Moneda pedida o, por defecto, la preferencia del usuario."""
    if moneda is not None:
        return moneda
    preferencia = await usuarios.obtener_preferencias(db, usuario)
    return preferencia.moneda


@router.get("/completo", response_model=PanelCompletoOut, summary="Panel completo")
async def panel_completo(
    usuario: UsuarioActual,
    db: DB,
    mes: str = Query(default=analysis.mes_actual(), pattern=PATRON_MES),
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> PanelCompletoOut:
    """Resumen + distribución + evolución + predicción + anomalías en una
    sola llamada (todo con datos reales del usuario autenticado)."""
    anio, num_mes = _descomponer_mes(mes)
    destino = await _moneda_vista(db, usuario, moneda)
    return await service.panel_completo(db, usuario.id, anio, num_mes, destino)


@router.get("/resumen", response_model=ResumenOut, summary="Resumen del mes")
async def resumen(
    usuario: UsuarioActual,
    db: DB,
    mes: str = Query(default=analysis.mes_actual(), pattern=PATRON_MES),
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> ResumenOut:
    """Totales del mes: ingresos, gastos, balance y cantidad de movimientos."""
    anio, num_mes = _descomponer_mes(mes)
    destino = await _moneda_vista(db, usuario, moneda)
    return await service.resumen_mensual(db, usuario.id, anio, num_mes, destino)


@router.get(
    "/gastos-por-categoria",
    response_model=list[CategoriaGastoOut],
    summary="Distribución de gastos por categoría (gráfico de dona)",
)
async def gastos_por_categoria(
    usuario: UsuarioActual,
    db: DB,
    mes: str = Query(default=analysis.mes_actual(), pattern=PATRON_MES),
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> list[CategoriaGastoOut]:
    """Gastos del mes agrupados por categoría, con su porcentaje."""
    anio, num_mes = _descomponer_mes(mes)
    destino = await _moneda_vista(db, usuario, moneda)
    return await service.gastos_por_categoria(db, usuario.id, anio, num_mes, destino)


@router.get(
    "/evolucion-mensual",
    response_model=EvolucionOut,
    summary="Evolución ingresos vs gastos (últimos 6 meses)",
)
async def evolucion_mensual(
    usuario: UsuarioActual,
    db: DB,
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> EvolucionOut:
    """Serie mensual (etiquetas 'YYYY-MM') de ingresos y gastos."""
    destino = await _moneda_vista(db, usuario, moneda)
    return await service.evolucion_mensual(db, usuario.id, destino)


@router.get(
    "/prediccion",
    response_model=PrediccionOut,
    summary="Predicción del gasto del próximo mes",
)
async def prediccion(
    usuario: UsuarioActual,
    db: DB,
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> PrediccionOut:
    """Regresión lineal sobre los gastos mensuales históricos."""
    destino = await _moneda_vista(db, usuario, moneda)
    return await analysis.predecir_gasto(db, usuario.id, destino)


@router.get(
    "/anomalias",
    response_model=AnomaliasOut,
    summary="Detección de movimientos anómalos",
)
async def anomalias(
    usuario: UsuarioActual,
    db: DB,
    moneda: Moneda | None = Query(default=None, description="Moneda de visualización"),
) -> AnomaliasOut:
    """Detecta movimientos atípicos con IsolationForest o z-score."""
    destino = await _moneda_vista(db, usuario, moneda)
    return await analysis.detectar_anomalias(db, usuario.id, destino)
