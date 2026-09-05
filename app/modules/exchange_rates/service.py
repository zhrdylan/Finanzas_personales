"""Servicio del módulo exchange_rates: caché + fallback + conversión.

Estrategia por conversión (misma moneda → 1 sin llamadas):

1. Caché exacta: tasa (base, quote, fecha) ya almacenada → ``cache``.
2. Proveedor: Frankfurter v2 para esa fecha → se persiste y devuelve
   ``proveedor`` (sin llamada HTTP por cada vista posterior).
3. Fallback: última tasa almacenada con fecha <= pedida → ``fallback``.
4. Sin nada válido → ``TasaNoDisponible`` (503 controlado, nunca inventar).

La fecha de referencia es la del movimiento (tasa histórica
determinística): no se guarda snapshot por fila porque es reproducible
desde el caché. Todas las operaciones monetarias usan ``Decimal``.
"""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exchange_rates import client, repository
from app.modules.exchange_rates.constants import DECIMALES_CONVERSION
from app.modules.exchange_rates.exceptions import (
    ProveedorTasasCaido,
    TasaNoDisponible,
    TasaSinDatos,
)
from app.modules.exchange_rates.schemas import ConversionOut, OrigenTasa, TasaOut
from app.shared.exceptions import EntradaInvalida
from app.shared.moneda import MONEDAS_VALIDAS

logger = logging.getLogger("app.exchange_rates.service")


def validar_moneda(moneda: str) -> str:
    """Normaliza y valida una moneda (COP/USD/EUR)."""
    codigo = (moneda or "").strip().upper()
    if codigo not in MONEDAS_VALIDAS:
        raise EntradaInvalida(f"Moneda inválida: {moneda}. Usa COP, USD o EUR")
    return codigo


def _a_tasa_out(tasa, origen: OrigenTasa) -> TasaOut:
    """Serializa una fila persistida con su origen."""
    return TasaOut(
        base=tasa.base_currency,  # type: ignore[arg-type]
        quote=tasa.quote_currency,  # type: ignore[arg-type]
        rate=Decimal(str(tasa.rate)),
        rate_date=tasa.rate_date,
        origen=origen,
    )


async def obtener_tasa(
    db: AsyncSession, base: str, quote: str, fecha: date | None = None
) -> TasaOut:
    """Tasa base → quote para la fecha (hoy si se omite)."""
    base = validar_moneda(base)
    quote = validar_moneda(quote)
    dia = fecha or date.today()

    if base == quote:
        return TasaOut(base=base, quote=quote, rate=Decimal("1"), rate_date=dia, origen="cache")  # type: ignore[arg-type]

    almacenada = await repository.obtener(db, base, quote, dia)
    if almacenada is not None:
        return _a_tasa_out(almacenada, "cache")

    try:
        tasa, fecha_real = await client.obtener_tasa(base, quote, dia)
    except (ProveedorTasasCaido, TasaSinDatos) as exc:
        logger.info("Proveedor sin tasa %s->%s @ %s (%s); usando fallback", base, quote, dia, exc)
        ultima = await repository.ultima_hasta(db, base, quote, dia)
        if ultima is None:
            raise TasaNoDisponible(f"Sin tasa {base}->{quote} para {dia} ni en caché") from exc
        return _a_tasa_out(ultima, "fallback")

    guardada = await repository.guardar(db, base=base, quote=quote, rate=tasa, rate_date=fecha_real)
    return _a_tasa_out(guardada, "proveedor")


async def convert(
    db: AsyncSession,
    monto: Decimal,
    desde: str,
    hacia: str,
    fecha: date | None = None,
) -> ConversionOut:
    """Convierte ``monto`` de ``desde`` a ``hacia`` (tasa histórica).

    Punto único de conversión del sistema: dashboard, metas, análisis y
    exports deben usar esta función y no reimplementarla.
    """
    desde = validar_moneda(desde)
    hacia = validar_moneda(hacia)
    tasa = await obtener_tasa(db, desde, hacia, fecha)
    convertido = (Decimal(str(monto)) * tasa.rate).quantize(
        Decimal("1." + "0" * DECIMALES_CONVERSION), rounding=ROUND_HALF_UP
    )
    return ConversionOut(
        monto_original=Decimal(str(monto)),
        moneda_original=desde,  # type: ignore[arg-type]
        monto_convertido=convertido,
        moneda_destino=hacia,  # type: ignore[arg-type]
        tasa=tasa.rate,
        fecha_tasa=tasa.rate_date,
        origen_tasa=tasa.origen,
    )
