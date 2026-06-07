"""Database session module.

This module configures the asynchronous SQLAlchemy engine and session factory,
and provides a FastAPI dependency for database sessions.
"""

from collections.abc import AsyncIterator

from loguru import logger
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
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped asynchronous database session.

    The session is automatically committed if the request completes
    successfully. If an exception occurs, the transaction is rolled back.

    Yields:
        AsyncSession: Asynchronous SQLAlchemy session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Database transaction failed")
            raise
