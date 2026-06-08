"""User repository module.

This module provides a repository for creating, reading, updating, and deleting
users in the database.
"""

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import User
from ai_notes_api.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user database operations."""

    async def create(self, user: User) -> User:
        """Create a user in the database.

        Args:
            user (User): User instance to persist.

        Returns:
            User: Persisted user with refreshed database-generated fields.
        """
        self.session.add(user)

        await self.session.flush()
        await self.session.refresh(user)

        logger.info("User created: id={}", user.id)

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Return a user by its identifier.

        Args:
            user_id (int): Unique user identifier.

        Returns:
            User | None: Matching user if found; otherwise, None.
        """
        stmt = select(User).where(User.id == user_id)

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            logger.debug("User not found: id={}", user_id)
        else:
            logger.debug("User found: id={}", user_id)

        return user

    async def get_by_email(self, user_email: str) -> User | None:
        """Return a user by its email.

        Args:
            user_email (str): User Email.

        Returns:
            User | None: Matching user if found; otherwise, None.
        """
        stmt = select(User).where(User.email == user_email)

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            logger.debug("User not found: email={}", user_email)
        else:
            logger.debug("User found: email={}", user_email)

        return user

    async def update(self, user: User) -> User:
        """Update an existing user in the database.

        Args:
            user (User): User instance with updated field values.

        Returns:
            User: Updated and refreshed user instance.
        """
        await self.session.flush()
        await self.session.refresh(user)

        logger.info("User updated: id={}", user.id)

        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the database.

        Args:
            user (User): User instance to delete.
        """
        await self.session.delete(user)
        await self.session.flush()

        logger.info("User deleted: id={}", user.id)
