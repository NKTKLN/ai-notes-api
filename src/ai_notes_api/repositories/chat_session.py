"""Chat session repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting chat sessions in the database.
"""

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update

from ai_notes_api.db.models import (
    ChatSession,
    ChatSessionGenerationStatus,
    GenerationJob,
    GenerationJobStatus,
    Message,
)
from ai_notes_api.repositories.base import BaseRepository
from ai_notes_api.repositories.filters import ChatSessionListFilters


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

    async def get_by_id(self, session_id: UUID) -> ChatSession | None:
        """Return a chat session by its identifier.

        Args:
            session_id (UUID): Unique chat session identifier.

        Returns:
            ChatSession | None: Matching chat session if found and not
            soft-deleted; otherwise, None.
        """
        stmt = (
            select(ChatSession)
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

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatSession | None:
        """Return a user's chat session by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.

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

    async def get_list(
        self,
        user_id: UUID,
        filters: ChatSessionListFilters,
    ) -> list[ChatSession]:
        """Return a paginated list of chat sessions.

        Args:
            user_id (UUID): Unique identifier of the user whose chat sessions
                are requested.
            filters (ChatSessionListFilters): Filters used to narrow the result set.

        Returns:
            list[ChatSession]: List of matching non-deleted chat sessions
            ordered by creation date in descending order.
        """
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.deleted_at.is_(None))
        )

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                search_value = f"%{search}%"
                stmt = stmt.where(ChatSession.title.ilike(search_value))

        stmt = (
            stmt.order_by(ChatSession.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )

        result = await self.session.execute(stmt)
        chat_sessions = list(result.scalars().all())

        logger.debug(
            (
                "Chat sessions list fetched: count={}, user_id={}, limit={}, "
                "offset={}, search={}"
            ),
            len(chat_sessions),
            user_id,
            filters.limit,
            filters.offset,
            filters.search,
        )

        return chat_sessions

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
        """Soft-delete a chat session and its related records.

        Sets the chat session and related message deletion timestamps instead of
        removing rows from the database. Active generation jobs of the chat
        session are marked as cancelled.

        Args:
            chat_session (ChatSession): Chat session instance to soft-delete.
        """
        now = datetime.now(UTC)

        chat_session.deleted_at = now
        chat_session.generation_status = ChatSessionGenerationStatus.IDLE
        chat_session.generation_id = None
        chat_session.generation_started_at = None

        await self.session.execute(
            update(Message)
            .where(Message.session_id == chat_session.id)
            .where(Message.deleted_at.is_(None))
            .values(deleted_at=now)
        )

        await self.session.execute(
            update(GenerationJob)
            .where(GenerationJob.session_id == chat_session.id)
            .where(
                GenerationJob.status.in_(
                    (
                        GenerationJobStatus.QUEUED,
                        GenerationJobStatus.RUNNING,
                    )
                )
            )
            .values(
                status=GenerationJobStatus.CANCELLED,
                finished_at=now,
            )
        )

        await self.session.flush()

        logger.info(
            "Chat session with related records soft-deleted: id={}",
            chat_session.id,
        )

    async def acquire_generation_lock(
        self,
        session_id: UUID,
        user_id: UUID,
        generation_id: UUID,
    ) -> bool:
        """Acquire a generation lock for a chat session.

        Args:
            session_id (UUID): Unique chat session identifier.
            user_id (UUID): Unique identifier of the user who owns the chat session.
            generation_id (UUID): Unique generation job identifier.

        Returns:
            bool: True if the lock was acquired; otherwise, False.
        """
        stmt = (
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.generation_status == ChatSessionGenerationStatus.IDLE)
            .where(ChatSession.deleted_at.is_(None))
            .values(
                generation_status=ChatSessionGenerationStatus.RUNNING,
                generation_id=generation_id,
                generation_started_at=datetime.now(UTC),
            )
            .returning(ChatSession.id)
        )

        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            logger.debug(
                "Generation lock was not acquired: session_id={}, generation_id={}",
                session_id,
                generation_id,
            )
        else:
            logger.info(
                "Generation lock acquired: session_id={}, generation_id={}",
                session_id,
                generation_id,
            )

        return row is not None

    async def release_generation_lock(
        self,
        session_id: UUID,
        user_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Release a generation lock for a chat session.

        Args:
            session_id (UUID): Unique chat session identifier.
            user_id (UUID): Unique identifier of the user who owns the chat session.
            generation_id (UUID): Unique generation job identifier that owns the lock.
        """
        stmt = (
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.generation_id == generation_id)
            .where(ChatSession.deleted_at.is_(None))
            .values(
                generation_status=ChatSessionGenerationStatus.IDLE,
                generation_id=None,
                generation_started_at=None,
            )
        )

        await self.session.execute(stmt)

        logger.info(
            "Generation lock released: session_id={}, generation_id={}",
            session_id,
            generation_id,
        )

    async def has_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> bool:
        """Return whether a generation job owns the chat session lock.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            generation_id (UUID): Unique generation job identifier.

        Returns:
            bool: True if the generation job owns the lock; otherwise, False.
        """
        stmt = (
            select(ChatSession.id)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
            .where(ChatSession.generation_id == generation_id)
            .where(ChatSession.generation_status == ChatSessionGenerationStatus.RUNNING)
            .where(ChatSession.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() is not None
