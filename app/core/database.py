"""Motor y sesión asíncrona de SQLAlchemy 2.0 (estilo declarativo).

Orientado exclusivamente a MySQL 9.6 con el driver asíncrono ``aiomysql``:
la conexión exige juego de caracteres utf8mb4, pre-ping y reciclaje de
conexiones para entornos como Laragon (MySQL local de larga vida).
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def utcnow() -> datetime:
    """Fecha y hora actual en UTC (ingenua, lista para almacenar en la BD)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos ORM."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # True solo para depurar el SQL generado
    pool_pre_ping=True,  # valida la conexión antes de usarla
    pool_recycle=3600,  # evita errores tipo "MySQL server has gone away"
    connect_args={"charset": "utf8mb4"},  # MySQL exige definir el charset
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # evita recargas lazy tras el commit (contexto async)
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: entrega una sesión por petición.

    Confirma la transacción si la petición terminó bien y la revierte si
    cualquier parte del flujo lanzó una excepción.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
