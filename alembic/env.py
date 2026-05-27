"""Alembic migration environment.

This module configures Alembic migrations for the application database,
including metadata discovery and offline or online migration execution.
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from ai_notes_api.core.config import settings
from ai_notes_api.db.models import Base
from alembic import context

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"

sys.path.append(str(SRC_DIR))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run database migrations in offline mode.

    Configures the Alembic context using only the database URL, without creating
    a database engine or requiring an active DBAPI connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an existing database connection.

    Args:
        connection: SQLAlchemy connection used by Alembic to execute migrations.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run database migrations using an asynchronous SQLAlchemy engine.

    Creates an asynchronous database engine from the Alembic configuration,
    opens a connection, runs synchronous Alembic migration logic through that
    connection, and disposes of the engine afterward.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run database migrations in online mode.

    Starts the asynchronous migration runner in a new event loop.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
