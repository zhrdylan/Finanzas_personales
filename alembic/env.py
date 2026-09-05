"""Entorno de Alembic configurado para SQLAlchemy asíncrono.

La URL de conexión se toma de la variable DATABASE_URL del archivo .env
(gestionada por app.core.config), nunca se escribe aquí.
Único dialecto soportado: MySQL 9.6 (driver aiomysql).
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Importa la configuración y los modelos de cada módulo para registrar el metadata
from app.core.config import settings
from app.core.database import Base
from app.modules.auth.models import RefreshToken  # noqa: F401
from app.modules.categories.models import Category  # noqa: F401
from app.modules.exchange_rates.models import ExchangeRate  # noqa: F401
from app.modules.goals.models import Meta  # noqa: F401
from app.modules.transactions.models import Transaction  # noqa: F401
from app.modules.users.models import Preferencia, User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline: genera el SQL sin conectarse a la BD."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection) -> None:  # noqa: ANN001 - conexión síncrona de Alembic
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Modo online: se conecta con el motor asíncrono y ejecuta las migraciones."""
    connectable = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
