"""Servicio del módulo analysis: lectura de datos y orquestación.

FRONTERA ARQUITECTÓNICA: este módulo SOLO LEE movimientos (SELECT) para
agregarlos y analizarlos. NUNCA crea, modifica ni elimina transacciones.

- La lectura de datos usa el ORM (consultas parametrizadas, seguras).
- El cálculo estadístico vive en ``motor.py`` (puro y testeable).
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.analysis import motor
from app.modules.analysis.schemas import AnomaliasOut, PrediccionOut
from app.modules.exchange_rates import service as tasas
from app.modules.transactions.models import Transaction


async def _leer_gastos(db: AsyncSession, usuario_id: int, moneda: str = "COP"):
    """Lee (fecha, monto convertido) de los gastos del usuario (solo lectura)."""
    filas = (
        await db.execute(
            select(Transaction.fecha, Transaction.monto, Transaction.moneda)
            .where(
                Transaction.usuario_id == usuario_id,
                Transaction.tipo == "gasto",
            )
            .order_by(Transaction.fecha)
        )
    ).all()
    convertidos = []
    for fecha, monto, moneda_origen in filas:
        conversion = await tasas.convert(db, monto, moneda_origen, moneda, fecha)
        convertidos.append((fecha, conversion.monto_convertido))
    return convertidos


async def _leer_movimientos(db: AsyncSession, usuario_id: int, moneda: str = "COP") -> list[dict]:
    """Lee los movimientos del usuario con montos en la moneda indicada."""
    movimientos = list(
        (
            await db.scalars(
                select(Transaction)
                .where(Transaction.usuario_id == usuario_id)
                .options(selectinload(Transaction.categoria))
                .order_by(Transaction.fecha.desc())
            )
        ).all()
    )
    leidos = []
    for m in movimientos:
        conversion = await tasas.convert(db, m.monto, m.moneda, moneda, m.fecha)
        leidos.append(
            {
                "id": m.id,
                "fecha": m.fecha,
                "descripcion": m.descripcion,
                "notas": m.notas,
                "tipo": m.tipo,
                "monto": conversion.monto_convertido,
                "moneda": moneda,
                "categoria": m.categoria.nombre,
                "metodo_pago": m.metodo_pago,
            }
        )
    return leidos


async def predecir_gasto(db: AsyncSession, usuario_id: int, moneda: str = "COP") -> PrediccionOut:
    """Predicción del gasto del próximo mes (regresión lineal)."""
    filas = await _leer_gastos(db, usuario_id, moneda)
    return motor.calcular_prediccion(filas)


async def detectar_anomalias(
    db: AsyncSession, usuario_id: int, moneda: str = "COP"
) -> AnomaliasOut:
    """Detección de movimientos anómalos (IsolationForest / Z modificado)."""
    movimientos = await _leer_movimientos(db, usuario_id, moneda)
    return motor.calcular_anomalias(movimientos)


def mes_actual() -> str:
    """Mes vigente en formato YYYY-MM (fecha del servidor)."""
    return date.today().strftime("%Y-%m")
