"""Dependencias transversales de FastAPI: sesión de base de datos."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

# Atajo de anotación para inyectar la sesión de BD en los endpoints
DB = Annotated[AsyncSession, Depends(get_db)]
