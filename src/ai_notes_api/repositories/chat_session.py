"""Chat session repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting chat sessions in the database.
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import ChatSession
from ai_notes_api.repositories import BaseRepository


class ChatSessionRepository(BaseRepository):
    """Repository for chat session database operations."""

    async def create(self, chat_session: ChatSession) -> ChatSession:
        """Create a chat session in the database.

        Args:
            chat_session (ChatSession): Chat session instance to persist.

        Returns:
            ChatSession: Persisted chat session with refreshed
            database-generated fields.
        """
        self.session.add(chat_session)

        await self.session.flush()
        await self.session.refresh(chat_session)

        logger.info("Chat session created: id={}", chat_session.id)

        return chat_session

    async def get_by_id(
        self,
        user_id: int,
        session_id: int,
    ) -> ChatSession | None:
        """Return a chat session by its identifier.

        Args:
            user_id (int): Unique identifier of the user who owns the chat session.
            session_id (int): Unique chat session identifier.

        Returns:
            ChatSession | None: Matching chat session if found and not
            soft-deleted; otherwise, None.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.id == session_id)
            .where(ChatSession.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        chat_session = result.scalar_one_or_none()

        if chat_session is None:
            logger.debug("Chat session not found: id={}", session_id)
        else:
            logger.debug("Chat session found: id={}", session_id)

        return chat_session

    async def update(self, chat_session: ChatSession) -> ChatSession:
        """Update an existing chat session in the database.

        Args:
            chat_session (ChatSession): Chat session instance with updated field values.

        Returns:
            ChatSession: Updated and refreshed chat session instance.
        """
        await self.session.flush()
        await self.session.refresh(chat_session)

        logger.info("Chat session updated: id={}", chat_session.id)

        return chat_session

    async def soft_delete(self, chat_session: ChatSession) -> None:
        """Soft-delete a chat session.

        Sets the chat session deletion timestamp instead of removing the row
        from the database.

        Args:
            chat_session (ChatSession): Chat session instance to soft-delete.
        """
        chat_session.deleted_at = datetime.now(UTC)

        await self.session.flush()

        logger.info("Chat session soft-deleted: id={}", chat_session.id)
