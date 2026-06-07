"""Test database fixtures."""

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ai_notes_api.core import settings
from ai_notes_api.db.models import Base


@pytest_asyncio.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """Create an asynchronous database session for tests.

    Creates a temporary database schema before each test, provides an async
    SQLAlchemy session, rolls back pending changes after the test, and disposes
    of the engine.

    Yields:
        AsyncSession: Asynchronous SQLAlchemy session used by tests.
    """
    engine = create_async_engine(settings.database_url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()
