"""Base repository module.

This module defines the base repository class used by application
repositories.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Base class for database repositories.

    Args:
        session (AsyncSession): Asynchronous SQLAlchemy session used to execute
            database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session (AsyncSession): Asynchronous SQLAlchemy session used by the
                repository.
        """
        self.session = session
