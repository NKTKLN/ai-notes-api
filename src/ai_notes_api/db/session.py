"""Database session module.

This module configures the asynchronous SQLAlchemy engine and session factory,
and provides a FastAPI dependency for database sessions.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from ai_notes_api.core import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


@asynccontextmanager
async def worker_session() -> AsyncIterator[AsyncSession]:
    """Provide a database session backed by a short-lived engine.

    Creates and disposes a dedicated NullPool engine within the current event
    loop, so it is safe to use inside Celery tasks that run each call in a fresh
    ``asyncio.run`` loop.

    Yields:
        AsyncSession: Asynchronous SQLAlchemy session.
    """
    worker_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        bind=worker_engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            yield session
    finally:
        await worker_engine.dispose()


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
            raise
