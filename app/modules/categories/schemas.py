"""Esquemas Pydantic del módulo categories."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoMovimiento = Literal["ingreso", "gasto"]


class CategoriaBase(BaseModel):
    """Campos comunes de una categoría."""

    nombre: str = Field(min_length=1, max_length=50, examples=["Alimentación"])
    tipo: TipoMovimiento
    color: str = Field(
        pattern=r"^#[0-9a-fA-F]{6}$",
        description="Color hexadecimal con formato #RRGGBB",
        examples=["#0053ce"],
    )
    # El icono es opcional: el diseño del prototipo solo usa nombre + color.
    icono: str = Field(default="", max_length=16, examples=["🛒"])


class CategoriaCreate(CategoriaBase):
    """Datos para crear una categoría."""


class CategoriaUpdate(BaseModel):
    """Datos parciales para editar una categoría (PATCH)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    tipo: TipoMovimiento | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    icono: str | None = Field(default=None, min_length=0, max_length=16)


class CategoriaOut(BaseModel):
    """Representación pública de una categoría."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tipo: TipoMovimiento
    color: str
    icono: str
    creado: datetime
