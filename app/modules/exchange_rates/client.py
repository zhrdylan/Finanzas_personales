"""Cliente del proveedor externo (Frankfurter v2, solo backend).

El frontend NUNCA llama aquí: todo el tráfico externo sale de este módulo.

API vigente (sin API key):
    GET {base_url}/rate/{BASE}/{QUOTE}[?date=YYYY-MM-DD]
    -> {"date": "2026-09-04", "base": "USD", "quote": "COP", "rate": 3144.98}

Sin ``date`` devuelve la última tasa publicada. Los errores de transporte
o 5xx se traducen a ``ProveedorTasasCaido``; un 404 o payload inválido a
``TasaSinDatos`` (el servicio aplica entonces el fallback a caché).
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx

from app.core.config import settings
from app.modules.exchange_rates.exceptions import ProveedorTasasCaido, TasaSinDatos

logger = logging.getLogger("app.exchange_rates.client")

_cliente_compartido: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Devuelve o inicializa el cliente HTTP persistente para tasas."""
    global _cliente_compartido
    if _cliente_compartido is None or _cliente_compartido.is_closed:
        _cliente_compartido = httpx.AsyncClient(timeout=settings.EXCHANGE_TIMEOUT_S)
    return _cliente_compartido


async def close_http_client() -> None:
    """Cierra el cliente HTTP persistente si está abierto (invocado en lifespan)."""
    global _cliente_compartido
    if _cliente_compartido is not None and not _cliente_compartido.is_closed:
        await _cliente_compartido.aclose()
        _cliente_compartido = None


def _validar_respuesta(datos: dict, base: str, quote: str) -> tuple[Decimal, date]:
    """Valida el payload v2 y devuelve (tasa, fecha) con tipos correctos."""
    try:
        tasa = Decimal(str(datos["rate"]))
        fecha = date.fromisoformat(str(datos["date"]))
    except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
        raise TasaSinDatos(f"Respuesta inválida del proveedor para {base}->{quote}") from exc
    if not tasa > 0:
        raise TasaSinDatos(f"Tasa inválida del proveedor para {base}->{quote}")
    if str(datos.get("base", "")).upper() != base or str(datos.get("quote", "")).upper() != quote:
        raise TasaSinDatos(f"El proveedor devolvió otro par distinto de {base}->{quote}")
    return tasa, fecha


async def obtener_tasa(base: str, quote: str, fecha: date | None = None) -> tuple[Decimal, date]:
    """Pide al proveedor la tasa del par (en la fecha o la última).

    Devuelve ``(tasa, fecha_real)``: la fecha real puede diferir de la
    pedida (el proveedor publica días hábiles).
    """
    base = base.upper()
    quote = quote.upper()
    url = f"{settings.EXCHANGE_BASE_URL.rstrip('/')}/rate/{base}/{quote}"
    params = {"date": fecha.isoformat()} if fecha is not None else None
    http = get_http_client()
    try:
        respuesta = await http.get(url, params=params)
    except httpx.HTTPError as exc:
        logger.warning("Proveedor de tasas sin respuesta (%s->%s): %s", base, quote, exc)
        raise ProveedorTasasCaido from exc

    if respuesta.status_code == 404:
        raise TasaSinDatos(f"Sin datos del proveedor para {base}->{quote}")
    if respuesta.status_code >= 400:
        logger.warning("Proveedor de tasas HTTP %s (%s->%s)", respuesta.status_code, base, quote)
        raise ProveedorTasasCaido(f"Proveedor de tasas HTTP {respuesta.status_code}")
    try:
        datos = respuesta.json()
    except ValueError as exc:
        raise TasaSinDatos(f"Respuesta no JSON del proveedor para {base}->{quote}") from exc
    if not isinstance(datos, dict):
        raise TasaSinDatos(f"Respuesta inesperada del proveedor para {base}->{quote}")
    return _validar_respuesta(datos, base, quote)
