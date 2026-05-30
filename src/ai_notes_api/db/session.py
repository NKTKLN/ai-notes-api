"""Database session module.

This module configures the asynchronous SQLAlchemy engine and session factory,
and provides a FastAPI dependency for database sessions.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_notes_api.core import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Provide an asynchronous database session.

    Creates an async SQLAlchemy session and yields it for request-scoped
    database operations.

    Yields:
        AsyncSession: Asynchronous SQLAlchemy session.
    """
    async with async_session_factory() as session:
        yield session
