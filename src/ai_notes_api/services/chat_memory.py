"""Chat memory service module.

This module provides business logic for retrieving and updating chat memory
records owned by users.
"""

from uuid import UUID

from ai_notes_api.db.models import ChatMemory
from ai_notes_api.exceptions import ChatMemoryNotFoundError
from ai_notes_api.repositories import ChatMemoryRepository
from ai_notes_api.schemas import ChatMemoryUpdateSchema


class ChatMemoryService:
    """Service for chat-memory-related business operations.

    Args:
        memory_repository (ChatMemoryRepository): Repository used to perform
            chat memory database operations.
    """

    def __init__(
        self,
        memory_repository: ChatMemoryRepository,
    ) -> None:
        """Initialize the chat memory service.

        Args:
            memory_repository (ChatMemoryRepository): Chat memory repository
                used by the service.
        """
        self.memories = memory_repository

    async def get_by_session_id(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatMemory:
        """Return a user's chat memory by chat session identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat memory.
            session_id (UUID): Unique identifier of the chat session.

        Returns:
            ChatMemory: Matching chat memory.

        Raises:
            ChatMemoryNotFoundError: If no accessible chat memory exists for the
                given chat session.
        """
        chat_memory = await self.memories.get_by_session_id_for_user(
            user_id=user_id,
            session_id=session_id,
        )

        if chat_memory is None:
            raise ChatMemoryNotFoundError()

        return chat_memory

    async def update_memory(
        self,
        user_id: UUID,
        session_id: UUID,
        data: ChatMemoryUpdateSchema,
    ) -> ChatMemory:
        """Update a user's chat memory.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat memory.
            session_id (UUID): Unique identifier of the chat session.
            data (ChatMemoryUpdateSchema): Validated data used to update the
                chat memory.

        Returns:
            ChatMemory: Updated chat memory.

        Raises:
            ChatMemoryNotFoundError: If no accessible chat memory exists for the
                given chat session.
        """
        memory = await self.get_by_session_id(user_id, session_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(memory, field, value)

        return await self.memories.update(memory)
