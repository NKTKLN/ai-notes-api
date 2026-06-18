"""Chat memory service module.

This module provides business logic for retrieving and updating chat memory
records owned by users.
"""

from uuid import UUID

from ai_notes_api.core import settings
from ai_notes_api.db.models import ChatMemory
from ai_notes_api.exceptions import (
    ChatMemoryDependenciesNotConfiguredError,
    ChatMemoryNotFoundError,
)
from ai_notes_api.llm.models import LLMMessage
from ai_notes_api.memory import MemoryExtractor, MemorySummarizer
from ai_notes_api.repositories import ChatMemoryRepository, MessageRepository


class ChatMemoryService:
    """Service for chat-memory-related business operations.

    Args:
        memories_repository (ChatMemoryRepository): Repository used to perform
            chat memory database operations.
        messages_repository (MessageRepository | None): Optional repository used
            to retrieve chat messages.
        extractor (MemoryExtractor | None): Optional service used to extract
            structured facts from chat context messages.
        summarizer (MemorySummarizer | None): Optional service used to update
            chat memory summaries from chat context messages.
    """

    def __init__(
        self,
        memories_repository: ChatMemoryRepository,
        messages_repository: MessageRepository | None = None,
        extractor: MemoryExtractor | None = None,
        summarizer: MemorySummarizer | None = None,
    ) -> None:
        """Initialize the chat memory service.

        Args:
            memories_repository (ChatMemoryRepository): Repository used to
                retrieve and update chat memory records.
            messages_repository (MessageRepository | None): Optional repository
                used to retrieve chat messages.
            extractor (MemoryExtractor | None): Optional service used to extract
                structured facts from chat context messages.
            summarizer (MemorySummarizer | None): Optional service used to update
                chat memory summaries from chat context messages.
        """
        self.messages = messages_repository
        self.memories = memories_repository
        self.extractor = extractor
        self.summarizer = summarizer

    async def _get_context_messages(
        self,
        user_id: UUID,
        session_id: UUID,
        message_id: UUID | None,
    ) -> list[LLMMessage]:
        """Get LLM context messages for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user.
            session_id (UUID): Unique identifier of the chat session.
            message_id (UUID | None): Identifier of the last summarized message.
                If None, context messages are loaded without a checkpoint.

        Returns:
            list[LLMMessage]: Context messages converted to the LLM message format.

        Raises:
            ChatMemoryDependenciesNotConfiguredError: If any dependency required for
                updating chat memory is missing.
        """
        if self.messages is None:
            raise ChatMemoryDependenciesNotConfiguredError()

        raw_messages = await self.messages.get_messages_after(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            limit=settings.llm_context_messages_limit,
        )

        return [
            LLMMessage(
                role=message.role,
                content=message.content,
            )
            for message in raw_messages
        ]

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

    async def update_memory(self, user_id: UUID, session_id: UUID) -> ChatMemory:
        """Update a user's chat memory from new chat messages.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat memory.
            session_id (UUID): Unique identifier of the chat session.

        Returns:
            ChatMemory: Updated chat memory.

        Raises:
            ChatMemoryNotFoundError: If no accessible chat memory exists for the
                given chat session.
            ChatMemoryDependenciesNotConfiguredError: If any dependency required for
                updating chat memory is missing.
        """
        if self.extractor is None or self.summarizer is None:
            raise ChatMemoryDependenciesNotConfiguredError()

        memory = await self.get_by_session_id(user_id, session_id)

        context_messages = await self._get_context_messages(
            user_id=user_id,
            session_id=session_id,
            message_id=memory.last_summarized_message_id,
        )

        if not context_messages:
            return memory

        if len(context_messages) >= settings.llm_context_messages_limit:
            memory.summary = (
                await self.summarizer.summarize(
                    summary=memory.summary,
                    context_messages=context_messages,
                )
                or memory.summary
            )

        memory.facts = (
            await self.extractor.extract(
                facts=memory.facts,
                context_messages=context_messages,
            )
            or memory.facts
        )

        return await self.memories.update(memory)
