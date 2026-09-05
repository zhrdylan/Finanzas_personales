"""Servicio del módulo dashboard: agregaciones del panel financiero.

Multi-moneda (Fase 2): cada movimiento se convierte a la moneda de
visualización con el servicio centralizado ``exchange_rates`` usando su
propia fecha (tasa histórica determinística). Los valores originales en
la base de datos nunca se modifican; solo los agregados se expresan en
la moneda pedida.
"""

import calendar
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis import service as analysis
from app.modules.categories.models import Category
from app.modules.dashboard.schemas import (
    CategoriaGastoOut,
    EvolucionOut,
    PanelCompletoOut,
    ResumenOut,
)
from app.modules.exchange_rates import service as tasas
from app.modules.transactions.models import Transaction

MESES_EVOLUCION = 6  # ventana del gráfico de línea


def _rango_mes(anio: int, mes: int) -> tuple[date, date]:
    """Primer y último día del mes indicado."""
    inicio = date(anio, mes, 1)
    fin = date(anio, mes, calendar.monthrange(anio, mes)[1])
    return inicio, fin


def _restar_meses(base: date, n: int) -> date:
    """Fecha equivalente a 'base' menos n meses (día 1)."""
    total = base.year * 12 + (base.month - 1) - n
    return date(total // 12, total % 12 + 1, 1)


def _a_decimal(valor: float) -> Decimal:
    """Convierte un float de Pandas a Decimal legible (2 decimales)."""
    return Decimal(str(round(float(valor), 2)))


async def _convertir(
    db: AsyncSession, monto: Decimal, moneda_origen: str, moneda: str, fecha: date
) -> Decimal:
    """Convierte un importe a la moneda de visualización (Decimal)."""
    if (moneda_origen or "COP").upper() == moneda:
        return Decimal(str(monto))
    conversion = await tasas.convert(db, Decimal(str(monto)), moneda_origen, moneda, fecha)
    return conversion.monto_convertido


async def resumen_mensual(
    db: AsyncSession, usuario_id: int, anio: int, mes: int, moneda: str = "COP"
) -> ResumenOut:
    """Totales del mes en la moneda indicada (conversión por movimiento)."""
    inicio, fin = _rango_mes(anio, mes)

    filas = (
        await db.execute(
            select(Transaction.tipo, Transaction.monto, Transaction.moneda, Transaction.fecha)
            .where(
                Transaction.usuario_id == usuario_id,
                Transaction.fecha >= inicio,
                Transaction.fecha <= fin,
            )
            .order_by(Transaction.fecha)
        )
    ).all()

    ingresos = Decimal("0")
    gastos = Decimal("0")
    for tipo, monto, moneda_origen, fecha in filas:
        valor = await _convertir(db, monto, moneda_origen, moneda, fecha)
        if tipo == "ingreso":
            ingresos += valor
        else:
            gastos += valor

    return ResumenOut(
        mes=f"{anio:04d}-{mes:02d}",
        total_ingresos=ingresos,
        total_gastos=gastos,
        balance=ingresos - gastos,
        cantidad_movimientos=len(filas),
        moneda=moneda,
    )


async def gastos_por_categoria(
    db: AsyncSession, usuario_id: int, anio: int, mes: int, moneda: str = "COP"
) -> list[CategoriaGastoOut]:
    """Gastos del mes agrupados por categoría, en la moneda indicada."""
    inicio, fin = _rango_mes(anio, mes)

    filas = (
        await db.execute(
            select(
                Category.id,
                Category.nombre,
                Category.color,
                Transaction.monto,
                Transaction.moneda,
                Transaction.fecha,
            )
            .join(Transaction, Transaction.categoria_id == Category.id)
            .where(
                Transaction.usuario_id == usuario_id,
                Transaction.tipo == "gasto",
                Transaction.fecha >= inicio,
                Transaction.fecha <= fin,
            )
        )
    ).all()

    agregados: dict[int, dict] = {}
    for categoria_id, nombre, color, monto, moneda_origen, fecha in filas:
        valor = await _convertir(db, monto, moneda_origen, moneda, fecha)
        actual = agregados.setdefault(
            categoria_id, {"nombre": nombre, "color": color, "total": Decimal("0")}
        )
        actual["total"] += valor

    total_gastos = sum((a["total"] for a in agregados.values()), Decimal("0"))
    resultado = [
        CategoriaGastoOut(
            categoria_id=categoria_id,
            nombre=a["nombre"],
            color=a["color"],
            total=a["total"],
            porcentaje=round(float(a["total"] / total_gastos * 100), 2)
            if total_gastos > 0
            else 0.0,
        )
        for categoria_id, a in agregados.items()
    ]
    resultado.sort(key=lambda c: c.total, reverse=True)
    return resultado


async def evolucion_mensual(db: AsyncSession, usuario_id: int, moneda: str = "COP") -> EvolucionOut:
    """Serie de los últimos 6 meses en la moneda indicada (Pandas)."""
    hoy = date.today()
    meses_claves = [
        _restar_meses(hoy, i).strftime("%Y-%m") for i in range(MESES_EVOLUCION - 1, -1, -1)
    ]
    inicio = _restar_meses(hoy, MESES_EVOLUCION - 1)

    filas = (
        await db.execute(
            select(
                Transaction.fecha, Transaction.tipo, Transaction.monto, Transaction.moneda
            ).where(
                Transaction.usuario_id == usuario_id,
                Transaction.fecha >= inicio,
            )
        )
    ).all()

    if not filas:
        ceros = [Decimal("0")] * MESES_EVOLUCION
        return EvolucionOut(meses=meses_claves, ingresos=ceros, gastos=ceros)

    convertidas = []
    for fecha, tipo, monto, moneda_origen in filas:
        valor = await _convertir(db, monto, moneda_origen, moneda, fecha)
        convertidas.append((fecha, tipo, valor))

    df = pd.DataFrame(convertidas, columns=["fecha", "tipo", "monto"])
    df["monto"] = df["monto"].astype(float)
    df["mes"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m")

    serie_ingresos = df[df["tipo"] == "ingreso"].groupby("mes")["monto"].sum()
    serie_gastos = df[df["tipo"] == "gasto"].groupby("mes")["monto"].sum()

    return EvolucionOut(
        meses=meses_claves,
        ingresos=[_a_decimal(serie_ingresos.get(m, 0.0)) for m in meses_claves],
        gastos=[_a_decimal(serie_gastos.get(m, 0.0)) for m in meses_claves],
    )


async def panel_completo(
    db: AsyncSession, usuario_id: int, anio: int, mes: int, moneda: str = "COP"
) -> PanelCompletoOut:
    """Agrupa los datos del panel en una sola respuesta (datos reales)."""
    resumen = await resumen_mensual(db, usuario_id, anio, mes, moneda)
    dona = await gastos_por_categoria(db, usuario_id, anio, mes, moneda)
    evolucion = await evolucion_mensual(db, usuario_id, moneda)
    prediccion = await analysis.predecir_gasto(db, usuario_id, moneda)
    anomalias = await analysis.detectar_anomalias(db, usuario_id, moneda)
    return PanelCompletoOut(
        resumen=resumen,
        gastos_por_categoria=dona,
        evolucion=evolucion,
        prediccion=prediccion,
        anomalias=anomalias,
        moneda=moneda,
    )
