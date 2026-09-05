"""Servicio del módulo categories: reglas de negocio de categorías."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.categories import repository
from app.modules.categories.models import Category
from app.modules.categories.schemas import CategoriaCreate, CategoriaUpdate
from app.shared.exceptions import Conflicto, NoEncontrado


async def listar(db: AsyncSession, usuario_id: int) -> list[Category]:
    """Lista las categorías del usuario autenticado."""
    return await repository.listar_por_usuario(db, usuario_id)


async def obtener(db: AsyncSession, usuario_id: int, categoria_id: int) -> Category:
    """Devuelve una categoría propia (404 si no existe o es ajena)."""
    categoria = await repository.obtener_propia(db, usuario_id, categoria_id)
    if categoria is None:
        raise NoEncontrado("Categoría no encontrada")
    return categoria


async def crear(db: AsyncSession, usuario_id: int, datos: CategoriaCreate) -> Category:
    """Crea una categoría propia (sin duplicar nombre + tipo)."""
    if await repository.buscar_duplicada(db, usuario_id, datos.nombre, datos.tipo):
        raise Conflicto("Ya existe una categoría con ese nombre y tipo")
    return await repository.crear(db, usuario_id, datos.model_dump())


async def actualizar(
    db: AsyncSession, usuario_id: int, categoria_id: int, datos: CategoriaUpdate
) -> Category:
    """Actualiza parcialmente una categoría propia."""
    categoria = await obtener(db, usuario_id, categoria_id)
    cambios = datos.model_dump(exclude_unset=True)

    nuevo_nombre = cambios.get("nombre", categoria.nombre)
    nuevo_tipo = cambios.get("tipo", categoria.tipo)

    # Si cambió nombre o tipo, validar que no quede duplicada
    if "nombre" in cambios or "tipo" in cambios:
        duplicada = await repository.buscar_duplicada(
            db, usuario_id, nuevo_nombre, nuevo_tipo, excluir_id=categoria.id
        )
        if duplicada is not None:
            raise Conflicto("Ya existe una categoría con ese nombre y tipo")

    # Si se pide cambiar el 'tipo' y la categoría ya tiene movimientos,
    # hay que rechazarlo (rompería la consistencia de los datos).
    tipo_cambiado = cambios.get("tipo") is not None and cambios["tipo"] != categoria.tipo
    if tipo_cambiado and await repository.contar_movimientos(db, categoria.id):
        raise Conflicto("No se puede cambiar el tipo: la categoría tiene movimientos asociados")

    for campo, valor in cambios.items():
        setattr(categoria, campo, valor)
    await db.flush()
    return categoria


async def eliminar(db: AsyncSession, usuario_id: int, categoria_id: int) -> None:
    """Elimina una categoría propia sin movimientos asociados."""
    categoria = await obtener(db, usuario_id, categoria_id)

    en_uso = await repository.contar_movimientos(db, categoria.id)
    if en_uso:
        raise Conflicto(
            f"La categoría tiene {en_uso} movimiento(s) asociado(s). "
            "Elimina o cambia la categoría de esos movimientos primero."
        )

    await repository.eliminar(db, categoria)
