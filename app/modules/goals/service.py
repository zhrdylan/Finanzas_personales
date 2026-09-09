"""Servicio del módulo goals: reglas de negocio de metas de ahorro.

Cálculos de progreso:
- ``porcentaje`` = monto_actual / monto_objetivo * 100 (puede superar 100).
- ``estado``     = 'cumplida' si monto_actual >= monto_objetivo; si no, 'activa'.
"""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.goals import repository
from app.modules.goals.models import Meta
from app.modules.goals.schemas import AporteCreate, MetaCreate, MetaOut, MetaUpdate
from app.shared.exceptions import EntradaInvalida, NoEncontrado

# Umbral (porcentaje) a partir del cual la UI marca la meta como "cercana"
UMBRAL_META_CERCANA = 80.0


def calcular_porcentaje(monto_actual: Decimal, monto_objetivo: Decimal) -> float:
    """Porcentaje de progreso (0.0 – ∞, redondeado a 2 decimales)."""
    if monto_objetivo <= 0:
        return 0.0
    return round(float(monto_actual / monto_objetivo * 100), 2)


def calcular_estado(monto_actual: Decimal, monto_objetivo: Decimal) -> str:
    """Estado de la meta: 'cumplida' cuando se alcanza el objetivo."""
    return "cumplida" if monto_actual >= monto_objetivo else "activa"


def a_out(meta: Meta) -> MetaOut:
    """Serializa la meta añadiendo porcentaje y estado calculados."""
    datos = MetaOut.model_validate(meta)
    return datos.model_copy(
        update={
            "porcentaje": calcular_porcentaje(meta.monto_actual, meta.monto_objetivo),
            "estado": calcular_estado(meta.monto_actual, meta.monto_objetivo),
        }
    )


async def listar(db: AsyncSession, usuario_id: int) -> list[MetaOut]:
    """Lista las metas del usuario autenticado con su progreso."""
    metas = await repository.listar_por_usuario(db, usuario_id)
    return [a_out(meta) for meta in metas]


async def obtener(db: AsyncSession, usuario_id: int, meta_id: int) -> MetaOut:
    """Devuelve una meta propia (404 si no existe o es ajena)."""
    meta = await repository.obtener_propia(db, usuario_id, meta_id)
    if meta is None:
        raise NoEncontrado("Meta no encontrada")
    return a_out(meta)


async def crear(db: AsyncSession, usuario_id: int, datos: MetaCreate) -> MetaOut:
    """Crea una meta de ahorro para el usuario autenticado."""
    meta = await repository.crear(
        db,
        usuario_id,
        nombre=datos.nombre.strip(),
        monto_objetivo=datos.monto_objetivo,
        monto_inicial=datos.monto_inicial,
        moneda=datos.moneda,
        fecha_limite=datos.fecha_limite,
    )
    return a_out(meta)


async def actualizar(db: AsyncSession, usuario_id: int, meta_id: int, datos: MetaUpdate) -> MetaOut:
    """Actualiza parcialmente una meta propia."""
    meta = await repository.obtener_propia(db, usuario_id, meta_id)
    if meta is None:
        raise NoEncontrado("Meta no encontrada")

    cambios = datos.model_dump(exclude_unset=True)
    objetivo_final = cambios.get("monto_objetivo", meta.monto_objetivo)
    actual_final = cambios.get("monto_actual", meta.monto_actual)

    if actual_final > objetivo_final:
        raise EntradaInvalida("El monto ahorrado no puede superar el monto objetivo en una edición")

    for campo, valor in cambios.items():
        setattr(meta, campo, valor)
    await db.flush()
    return a_out(meta)


async def registrar_aporte(
    db: AsyncSession, usuario_id: int, meta_id: int, datos: AporteCreate
) -> MetaOut:
    """Registra progreso con incremento atómico a nivel SQL.

    Delega la suma al motor (``UPDATE ... SET monto_actual =
    monto_actual + :monto``) en vez de leer-modificar-escribir en memoria,
    eliminando la condición de carrera de aportes concurrentes.
    """
    meta = await repository.abonar_atomico(db, usuario_id, meta_id, datos.monto)
    if meta is None:
        raise NoEncontrado("Meta no encontrada")
    return a_out(meta)


async def eliminar(db: AsyncSession, usuario_id: int, meta_id: int) -> None:
    """Elimina una meta propia."""
    meta = await repository.obtener_propia(db, usuario_id, meta_id)
    if meta is None:
        raise NoEncontrado("Meta no encontrada")
    await repository.eliminar(db, meta)
