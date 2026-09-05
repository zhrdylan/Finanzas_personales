"""Esquema genérico de paginación compartido por varios módulos."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    """Respuesta paginada estándar de la API."""

    items: list[T]
    total: int
    pagina: int
    por_pagina: int
    total_paginas: int
