"""Message service module.

This module provides business logic for working with messages.
"""

from uuid import UUID

from ai_notes_api.db.models import Message, MessageRole
from ai_notes_api.exceptions import ChatSessionNotFoundError, MessageNotFoundError
from ai_notes_api.repositories import (
    ChatSessionRepository,
    MessageListFilters,
    MessageRepository,
)
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    MessageListQuerySchema,
    UserMessageCreateSchema,
)


class MessageService:
    """Service for message-related business operations.

    Args:
        message_repository (MessageRepository): Repository used to perform
            message database operations.
        session_repository (ChatSessionRepository): Repository used to validate
            chat session access.
    """

    def __init__(
        self,
        message_repository: MessageRepository,
        session_repository: ChatSessionRepository,
    ) -> None:
        """Initialize the message service.

        Args:
            message_repository (MessageRepository): Message repository used by
                the service.
            session_repository (ChatSessionRepository): Chat session repository
                used by the service.
        """
        self.messages = message_repository
        self.sessions = session_repository

    async def _ensure_session_owner(self, user_id: UUID, session_id: UUID) -> None:
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

    async def create_user_message(
        self,
        user_id: UUID,
        data: UserMessageCreateSchema,
    ) -> Message:
        """Create a user message.

        Args:
            user_id (UUID): Unique identifier of the user creating the message.
            data (UserMessageCreateSchema): Validated data used to create the
                user message.

        Returns:
            Message: Created user message.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self._ensure_session_owner(user_id, data.session_id)

        message = Message(
            session_id=data.session_id,
            content=data.content,
            role=MessageRole.USER,
        )

        return await self.messages.create(message)

    async def create_assistant_message(
        self,
        user_id: UUID,
        data: AssistantMessageCreateSchema,
    ) -> Message:
        """Create an assistant message.

        Args:
            user_id (UUID): Unique identifier of the user creating the message.
            data (AssistantMessageCreateSchema): Validated data used to create
                the assistant message.

        Returns:
            Message: Created assistant message.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self._ensure_session_owner(user_id, data.session_id)

        message = Message(
            session_id=data.session_id,
            content=data.content,
            role=MessageRole.ASSISTANT,
            model_name=data.model_name,
            provider=data.provider,
            prompt_tokens=data.prompt_tokens,
            completion_tokens=data.completion_tokens,
            total_tokens=data.total_tokens,
        )

        return await self.messages.create(message)

    async def get_messages_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: MessageListQuerySchema,
    ) -> list[Message]:
        """Return a list of messages matching the given filters.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            filters (MessageListQuerySchema): API filters and pagination parameters.

        Returns:
            list[Message]: List of matching messages.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self._ensure_session_owner(user_id, session_id)

        repository_filters = MessageListFilters(
            search=filters.search,
            limit=filters.limit,
            offset=filters.offset,
            role=filters.role,
            model_name=filters.model_name,
            provider=filters.provider,
        )

        return await self.messages.get_list(user_id, session_id, repository_filters)

    async def get_message(self, user_id: UUID, message_id: UUID) -> Message:
        """Return a message by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the message.
            message_id (UUID): Unique message identifier.

        Returns:
            Message: Matching message.

        Raises:
            MessageNotFoundError: If no message with the given identifier exists.
        """
        message = await self.messages.get_by_id_for_user(user_id, message_id)

        if message is None:
            raise MessageNotFoundError()

        return message

    async def get_context_messages(
        self,
        user_id: UUID,
        session_id: UUID,
        limit: int = 20,
    ) -> list[Message]:
        """Return recent context messages in chronological order.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            limit (int): Maximum number of recent messages to return.

        Returns:
            list[Message]: Recent non-deleted messages ordered from oldest to newest.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self._ensure_session_owner(user_id, session_id)

        messages = await self.messages.get_last_messages(
            user_id=user_id,
            session_id=session_id,
            limit=limit,
        )

        return list(reversed(messages))

    async def delete_message(self, user_id: UUID, message_id: UUID) -> None:
        """Delete a message by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the message.
            message_id (UUID): Unique message identifier to delete.

        Raises:
            MessageNotFoundError: If no message with the given identifier exists.
        """
        message = await self.messages.get_by_id_for_user(user_id, message_id)

        if message is None:
            raise MessageNotFoundError()

        await self.messages.soft_delete(message)
