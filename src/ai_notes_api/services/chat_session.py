"""Chat session service module.

This module provides business logic for working with chat sessions.
"""

from uuid import UUID

from ai_notes_api.db.models import ChatMemory, ChatSession, ChatSessionGenerationStatus
from ai_notes_api.exceptions import (
    ChatSessionNotFoundError,
    GenerationInProgressError,
    GenerationNotFoundError,
)
from ai_notes_api.repositories import (
    ChatMemoryRepository,
    ChatSessionListFilters,
    ChatSessionRepository,
)
from ai_notes_api.schemas import (
    ChatSessionCreateSchema,
    ChatSessionListQuerySchema,
    ChatSessionUpdateSchema,
)


class ChatSessionService:
    """Service for chat session-related business operations.

    Args:
        repository (ChatSessionRepository): Repository used to perform chat
            session database operations.
    """

    def __init__(
        self,
        session_repository: ChatSessionRepository,
        memory_repository: ChatMemoryRepository,
    ) -> None:
        """Initialize the chat session service.

        Args:
            repository (ChatSessionRepository): Chat session repository used by
                the service.
        """
        self.sessions = session_repository
        self.memories = memory_repository

    async def create_chat_session(
        self,
        user_id: UUID,
        data: ChatSessionCreateSchema,
    ) -> ChatSession:
        """Create a chat session.

        Args:
            user_id (UUID): Unique identifier of the user creating the chat session.
            data (ChatSessionCreateSchema): Validated data used to create the
                chat session.

        Returns:
            ChatSession: Created chat session instance.
        """
        chat_session = ChatSession(
            user_id=user_id,
            title=data.title,
        )

        session = await self.sessions.create(chat_session)

        chat_memory = ChatMemory(session_id=session.id)

        await self.memories.create(chat_memory)

        return session

    async def get_chat_sessions_list(
        self,
        user_id: UUID,
        filters: ChatSessionListQuerySchema,
    ) -> list[ChatSession]:
        """Return a list of chat sessions matching the given filters.

        Args:
            user_id (UUID): Unique identifier of the user whose chat sessions
                are requested.
            filters (ChatSessionListQuerySchema): API filters and pagination parameters.

        Returns:
            list[ChatSession]: List of matching chat sessions.
        """
        repository_filters = ChatSessionListFilters(
            search=filters.search,
            limit=filters.limit,
            offset=filters.offset,
        )

        return await self.sessions.get_list(user_id, repository_filters)

    async def get_chat_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatSession:
        """Return a chat session by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.

        Returns:
            ChatSession: Matching chat session.

        Raises:
            ChatSessionNotFoundError: If no chat session with the given
                identifier exists.
        """
        chat_session = await self.sessions.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        return chat_session

    async def update_chat_session(
        self,
        user_id: UUID,
        session_id: UUID,
        data: ChatSessionUpdateSchema,
    ) -> ChatSession:
        """Update a chat session by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            data (ChatSessionUpdateSchema): Validated chat session update data.

        Returns:
            ChatSession: Updated chat session.

        Raises:
            ChatSessionNotFoundError: If no chat session with the given
                identifier exists.
        """
        chat_session = await self.sessions.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(chat_session, field, value)

        await self.sessions.update(chat_session)

        return chat_session

    async def delete_chat_session(self, user_id: UUID, session_id: UUID) -> None:
        """Delete a chat session by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier to delete.

        Raises:
            ChatSessionNotFoundError: If no chat session with the given
                identifier exists.
        """
        chat_session = await self.sessions.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        await self.sessions.soft_delete(chat_session)

    async def acquire_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Acquire a generation lock for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            generation_id (UUID): Unique generation job identifier.

        Raises:
            GenerationInProgressError: If generation is already in progress.
        """
        lock_acquired = await self.sessions.acquire_generation_lock(
            user_id=user_id,
            session_id=session_id,
            generation_id=generation_id,
        )

        if not lock_acquired:
            raise GenerationInProgressError()

    async def release_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Release a generation lock for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            generation_id (UUID): Unique generation job identifier that owns the lock.
        """
        await self.sessions.release_generation_lock(
            user_id=user_id,
            session_id=session_id,
            generation_id=generation_id,
        )

    async def ensure_session_owner(self, user_id: UUID, session_id: UUID) -> None:
        """Ensure that a chat session belongs to a user.

        Args:
            user_id (UUID): Unique identifier of the user who should own the
                chat session.
            session_id (UUID): Unique chat session identifier.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        chat_session = await self.sessions.get_by_id_for_user(
            user_id,
            session_id,
        )

        if chat_session is None:
            raise ChatSessionNotFoundError()

    async def ensure_no_active_job(self, user_id: UUID, session_id: UUID) -> None:
        """Ensure that no active generation job exists for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the session.
            session_id (UUID): Unique chat session identifier.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
            GenerationInProgressError: If a QUEUED or RUNNING job already exists.
        """
        chat_session = await self.sessions.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        if chat_session.generation_status == ChatSessionGenerationStatus.RUNNING:
            raise GenerationInProgressError()

    async def ensure_generation_lock_owner(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Ensure that a generation job owns the chat session lock.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat
                session.
            session_id (UUID): Unique chat session identifier.
            generation_id (UUID): Unique generation job identifier.

        Raises:
            GenerationNotFoundError: If the generation job does not own the lock.
        """
        owns_lock = await self.sessions.has_generation_lock(
            user_id=user_id,
            session_id=session_id,
            generation_id=generation_id,
        )

        if not owns_lock:
            raise GenerationNotFoundError()
