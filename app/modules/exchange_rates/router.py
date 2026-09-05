"""Router del módulo exchange_rates: consulta de tasas (delgado, sin lógica).

El frontend NUNCA llama a Frankfurter: este endpoint expone las tasas
resueltas por el backend (caché + proveedor + fallback) para
transparencia (p. ej. mostrar la tasa usada en un reporte).
"""

from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.exchange_rates import service
from app.modules.exchange_rates.schemas import TasaOut

router = APIRouter(prefix="/tasas", tags=["tasas de cambio"])

PATRON_MONEDA = r"^[A-Za-z]{3}$"


@router.get("", response_model=TasaOut, summary="Obtener tasa de cambio")
async def obtener_tasa(
    usuario: UsuarioActual,
    db: DB,
    base: str = Query(description="Moneda origen (COP, USD, EUR)", pattern=PATRON_MONEDA),
    quote: str = Query(description="Moneda destino (COP, USD, EUR)", pattern=PATRON_MONEDA),
    fecha: date | None = Query(default=None, description="Fecha histórica (por defecto: hoy)"),
) -> TasaOut:
    """Tasa base → quote (caché, proveedor o fallback; 503 sin datos)."""
    return await service.obtener_tasa(db, base, quote, fecha)
