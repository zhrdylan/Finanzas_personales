"""Router del módulo categories: CRUD de categorías (delgado, sin lógica)."""

from fastapi import APIRouter, status

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.categories import service
from app.modules.categories.models import Category
from app.modules.categories.schemas import CategoriaCreate, CategoriaOut, CategoriaUpdate

router = APIRouter(prefix="/categorias", tags=["categorías"])


@router.get("", response_model=list[CategoriaOut], summary="Listar categorías")
async def listar(usuario: UsuarioActual, db: DB) -> list[Category]:
    """Lista las categorías del usuario (ingresos y gastos)."""
    return await service.listar(db, usuario.id)


@router.post(
    "",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear categoría",
)
async def crear(datos: CategoriaCreate, usuario: UsuarioActual, db: DB) -> Category:
    """Crea una categoría nueva para el usuario autenticado."""
    return await service.crear(db, usuario.id, datos)


@router.get("/{categoria_id}", response_model=CategoriaOut, summary="Ver una categoría")
async def obtener(categoria_id: int, usuario: UsuarioActual, db: DB) -> Category:
    """Devuelve una categoría propia por id (404 si es de otro usuario)."""
    return await service.obtener(db, usuario.id, categoria_id)


@router.patch("/{categoria_id}", response_model=CategoriaOut, summary="Actualizar categoría")
async def actualizar(
    categoria_id: int,
    datos: CategoriaUpdate,
    usuario: UsuarioActual,
    db: DB,
) -> Category:
    """Actualiza parcialmente una categoría propia."""
    return await service.actualizar(db, usuario.id, categoria_id, datos)


@router.delete(
    "/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar categoría",
)
async def eliminar(categoria_id: int, usuario: UsuarioActual, db: DB) -> None:
    """Elimina una categoría propia sin movimientos asociados."""
    await service.eliminar(db, usuario.id, categoria_id)
