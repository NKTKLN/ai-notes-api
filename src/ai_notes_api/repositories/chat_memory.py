"""Chat memory repository module.

This module provides a repository for creating, reading, and updating chat
memory records in the database.
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import ChatMemory, ChatSession
from ai_notes_api.repositories.base import BaseRepository


class ChatMemoryRepository(BaseRepository):
    """Repository for chat memory database operations."""

    async def create(self, chat_memory: ChatMemory) -> ChatMemory:
        """Create a chat memory record in the database.

        Args:
            chat_memory (ChatMemory): Chat memory instance to persist.

        Returns:
            ChatMemory: Persisted chat memory with refreshed database-generated
            fields.
        """
        self.session.add(chat_memory)

        await self.session.flush()
        await self.session.refresh(chat_memory)

        logger.info("Chat memory created: id={}", chat_memory.id)

        return chat_memory

    async def get_by_session_id(self, session_id: UUID) -> ChatMemory | None:
        """Return chat memory by chat session identifier.

        Args:
            session_id (UUID): Unique chat session identifier.

        Returns:
            ChatMemory | None: Matching chat memory if found and the chat
            session is not soft-deleted; otherwise, None.
        """
        stmt = (
            select(ChatMemory)
            .join(ChatSession, ChatSession.id == ChatMemory.session_id)
            .where(ChatMemory.session_id == session_id)
            .where(ChatSession.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        chat_memory = result.scalar_one_or_none()

        if chat_memory is None:
            logger.debug("Chat memory not found: session_id={}", session_id)
        else:
            logger.debug("Chat memory found: session_id={}", session_id)

        return chat_memory

    async def get_by_session_id_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatMemory | None:
        """Return a user's chat memory by chat session identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat
                session.
            session_id (UUID): Unique chat session identifier.

        Returns:
            ChatMemory | None: Matching chat memory if found and the chat
            session is accessible; otherwise, None.
        """
        stmt = (
            select(ChatMemory)
            .join(ChatSession, ChatSession.id == ChatMemory.session_id)
            .where(ChatMemory.session_id == session_id)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        chat_memory = result.scalar_one_or_none()

        if chat_memory is None:
            logger.debug("Chat memory not found: session_id={}", session_id)
        else:
            logger.debug("Chat memory found: session_id={}", session_id)

        return chat_memory

    async def update(self, chat_memory: ChatMemory) -> ChatMemory:
        """Update an existing chat memory record in the database.

        Args:
            chat_memory (ChatMemory): Chat memory instance with updated field
                values.

        Returns:
            ChatMemory: Updated and refreshed chat memory instance.
        """
        await self.session.flush()
        await self.session.refresh(chat_memory)

        logger.info("Chat memory updated: id={}", chat_memory.id)

        return chat_memory
