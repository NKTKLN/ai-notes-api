"""Chat session service module.

This module provides business logic for working with chat sessions.
"""

from uuid import UUID

from ai_notes_api.db.models import ChatSession
from ai_notes_api.exceptions import ChatSessionNotFoundError
from ai_notes_api.repositories import ChatSessionListFilters, ChatSessionRepository
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

    def __init__(self, repository: ChatSessionRepository) -> None:
        """Initialize the chat session service.

        Args:
            repository (ChatSessionRepository): Chat session repository used by
                the service.
        """
        self.repository = repository

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

        return await self.repository.create(chat_session)

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

        return await self.repository.get_list(user_id, repository_filters)

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
        chat_session = await self.repository.get_by_id_for_user(user_id, session_id)

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
        chat_session = await self.repository.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(chat_session, field, value)

        await self.repository.update(chat_session)

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
        chat_session = await self.repository.get_by_id_for_user(user_id, session_id)

        if chat_session is None:
            raise ChatSessionNotFoundError()

        await self.repository.soft_delete(chat_session)
