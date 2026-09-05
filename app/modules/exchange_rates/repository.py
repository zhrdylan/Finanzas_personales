"""Repositorio del módulo exchange_rates: caché de tasas en MySQL.

Las tasas son globales (no pertenecen a ningún usuario): no hay filtro
por ``usuario_id`` aquí, a diferencia de los módulos de negocio.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.exchange_rates.constants import FUENTE_TASAS
from app.modules.exchange_rates.models import ExchangeRate


async def obtener(db: AsyncSession, base: str, quote: str, fecha: date) -> ExchangeRate | None:
    """Tasa exacta del par en la fecha indicada (caché)."""
    return await db.scalar(
        select(ExchangeRate).where(
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
            ExchangeRate.rate_date == fecha,
        )
    )


async def ultima_hasta(db: AsyncSession, base: str, quote: str, fecha: date) -> ExchangeRate | None:
    """Última tasa del par en fecha <= indicada (fallback histórico)."""
    return await db.scalar(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == base,
            ExchangeRate.quote_currency == quote,
            ExchangeRate.rate_date <= fecha,
        )
        .order_by(ExchangeRate.rate_date.desc())
        .limit(1)
    )


async def guardar(
    db: AsyncSession,
    *,
    base: str,
    quote: str,
    rate: Decimal,
    rate_date: date,
    source: str = FUENTE_TASAS,
) -> ExchangeRate:
    """Inserta o actualiza la tasa del par/fecha (sin duplicados)."""
    existente = await obtener(db, base, quote, rate_date)
    if existente is not None:
        existente.rate = rate
        existente.source = source
        await db.flush()
        return existente
    tasa = ExchangeRate(
        base_currency=base,
        quote_currency=quote,
        rate=rate,
        rate_date=rate_date,
        source=source,
    )
    db.add(tasa)
    await db.flush()
    return tasa
