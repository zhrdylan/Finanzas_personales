"""Router del módulo goals: CRUD de metas de ahorro + aportes (delgado)."""

from fastapi import APIRouter, status

from app.core.deps import DB
from app.modules.auth.dependencies import UsuarioActual
from app.modules.goals import service
from app.modules.goals.schemas import AporteCreate, MetaCreate, MetaOut, MetaUpdate

router = APIRouter(prefix="/metas", tags=["metas de ahorro"])


@router.get("", response_model=list[MetaOut], summary="Listar metas de ahorro")
async def listar(usuario: UsuarioActual, db: DB) -> list[MetaOut]:
    """Lista las metas del usuario con su porcentaje y estado de progreso."""
    return await service.listar(db, usuario.id)


@router.post(
    "",
    response_model=MetaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear meta de ahorro",
)
async def crear(datos: MetaCreate, usuario: UsuarioActual, db: DB) -> MetaOut:
    """Crea una meta nueva (nombre, monto objetivo, ahorro inicial y fecha)."""
    return await service.crear(db, usuario.id, datos)


@router.get("/{meta_id}", response_model=MetaOut, summary="Ver una meta")
async def obtener(meta_id: int, usuario: UsuarioActual, db: DB) -> MetaOut:
    """Devuelve una meta propia por id con su progreso."""
    return await service.obtener(db, usuario.id, meta_id)


@router.patch("/{meta_id}", response_model=MetaOut, summary="Editar meta")
async def actualizar(meta_id: int, datos: MetaUpdate, usuario: UsuarioActual, db: DB) -> MetaOut:
    """Actualiza parcialmente una meta propia."""
    return await service.actualizar(db, usuario.id, meta_id, datos)


@router.post(
    "/{meta_id}/aportes",
    response_model=MetaOut,
    summary="Registrar aporte (progreso)",
)
async def registrar_aporte(
    meta_id: int, datos: AporteCreate, usuario: UsuarioActual, db: DB
) -> MetaOut:
    """Suma el monto indicado al ahorro acumulado de la meta propia."""
    return await service.registrar_aporte(db, usuario.id, meta_id, datos)


@router.delete(
    "/{meta_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar meta",
)
async def eliminar(meta_id: int, usuario: UsuarioActual, db: DB) -> None:
    """Elimina una meta propia."""
    await service.eliminar(db, usuario.id, meta_id)
