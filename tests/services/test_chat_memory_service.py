"""Tests for chat memory service."""

from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import ChatMemory, MessageRole
from ai_notes_api.exceptions import (
    ChatMemoryDependenciesNotConfiguredError,
    ChatMemoryNotFoundError,
)
from ai_notes_api.llm.schemas import LLMMessage
from ai_notes_api.memory import MemoryExtractor, MemorySummarizer
from ai_notes_api.repositories import ChatMemoryRepository, MessageRepository
from ai_notes_api.services import ChatMemoryService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MEMORY_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_LAST_MESSAGE_ID = UUID("55555555-5555-5555-5555-555555555555")


class FakeChatMemoryRepository:
    """Fake chat memory repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize the fake repository."""
        self.memories: dict[tuple[UUID, UUID], ChatMemory] = {}
        self.updated_memory: ChatMemory | None = None

    async def get_by_session_id_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatMemory | None:
        """Return a user's chat memory by chat session identifier."""
        return self.memories.get((user_id, session_id))

    async def update(self, chat_memory: ChatMemory) -> ChatMemory:
        """Record and return the updated chat memory."""
        self.updated_memory = chat_memory
        return chat_memory


class FakeMessageRepository:
    """Fake message repository returning a configurable set of messages."""

    def __init__(self, messages: list[SimpleNamespace] | None = None) -> None:
        """Initialize the fake repository.

        Args:
            messages (list[SimpleNamespace] | None): Messages returned by
                get_messages_after.
        """
        self.messages = messages if messages is not None else []
        self.call_kwargs: dict[str, Any] | None = None

    async def get_messages_after(
        self,
        user_id: UUID,
        session_id: UUID,
        message_id: UUID | None,
        limit: int | None = None,
    ) -> list[SimpleNamespace]:
        """Record arguments and return the configured messages."""
        self.call_kwargs = {
            "user_id": user_id,
            "session_id": session_id,
            "message_id": message_id,
            "limit": limit,
        }
        return self.messages


class FakeExtractor:
    """Fake memory extractor returning a configurable fact list."""

    def __init__(self, facts: list[dict[str, Any]] | None = None) -> None:
        """Initialize the fake extractor."""
        self.facts = (
            facts if facts is not None else [{"key": "city", "value": "Berlin"}]
        )
        self.call_kwargs: dict[str, Any] | None = None

    async def extract(
        self,
        facts: list[dict[str, Any]],
        context_messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        """Record arguments and return the configured facts."""
        self.call_kwargs = {"facts": facts, "context_messages": context_messages}
        return self.facts


class FakeSummarizer:
    """Fake memory summarizer returning a configurable summary."""

    def __init__(self, summary: str = "New summary") -> None:
        """Initialize the fake summarizer."""
        self.summary = summary
        self.call_kwargs: dict[str, Any] | None = None
        self.called = False

    async def summarize(
        self,
        summary: str,
        context_messages: list[LLMMessage],
    ) -> str:
        """Record arguments and return the configured summary."""
        self.called = True
        self.call_kwargs = {"summary": summary, "context_messages": context_messages}
        return self.summary


def _messages(count: int) -> list[SimpleNamespace]:
    """Return a list of fake chat messages.

    Args:
        count (int): Number of messages to build.

    Returns:
        list[SimpleNamespace]: Fake messages exposing role and content.
    """
    return [
        SimpleNamespace(role=MessageRole.USER, content=f"Message {index}")
        for index in range(count)
    ]


def _build_service(
    *,
    messages: list[SimpleNamespace] | None = None,
    extractor: FakeExtractor | None = None,
    summarizer: FakeSummarizer | None = None,
    with_dependencies: bool = True,
) -> tuple[
    FakeChatMemoryRepository,
    FakeMessageRepository,
    FakeExtractor,
    FakeSummarizer,
    ChatMemoryService,
]:
    """Build a chat memory service wired with fake collaborators.

    Args:
        messages (list[SimpleNamespace] | None): Messages returned by the fake
            message repository.
        extractor (FakeExtractor | None): Fake extractor to use.
        summarizer (FakeSummarizer | None): Fake summarizer to use.
        with_dependencies (bool): Whether to wire update dependencies.

    Returns:
        tuple: Fake collaborators and the configured service.
    """
    memories_repository = FakeChatMemoryRepository()
    messages_repository = FakeMessageRepository(messages)
    extractor = extractor or FakeExtractor()
    summarizer = summarizer or FakeSummarizer()

    if with_dependencies:
        service = ChatMemoryService(
            memories_repository=cast(ChatMemoryRepository, memories_repository),
            messages_repository=cast(MessageRepository, messages_repository),
            extractor=cast(MemoryExtractor, extractor),
            summarizer=cast(MemorySummarizer, summarizer),
        )
    else:
        service = ChatMemoryService(
            memories_repository=cast(ChatMemoryRepository, memories_repository),
        )

    return memories_repository, messages_repository, extractor, summarizer, service


def _chat_memory(
    *,
    summary: str = "Existing summary",
    facts: list[dict[str, Any]] | None = None,
    last_summarized_message_id: UUID | None = None,
) -> ChatMemory:
    """Return a chat memory model instance for service tests.

    Args:
        summary (str): Chat memory summary.
        facts (list[dict[str, Any]] | None): Structured chat memory facts.
        last_summarized_message_id (UUID | None): Last summarized message id.

    Returns:
        ChatMemory: Chat memory model instance.
    """
    return ChatMemory(
        id=TEST_MEMORY_ID,
        session_id=TEST_SESSION_ID,
        summary=summary,
        facts=facts if facts is not None else [{"key": "name", "value": "Alex"}],
        last_summarized_message_id=last_summarized_message_id,
    )


@pytest.mark.asyncio
async def test_get_by_session_id_returns_memory() -> None:
    """Test that an accessible chat memory is returned."""
    repository, _, _, _, service = _build_service()
    memory = _chat_memory()
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    result = await service.get_by_session_id(TEST_USER_ID, TEST_SESSION_ID)

    assert result is memory


@pytest.mark.asyncio
async def test_get_by_session_id_raises_when_missing() -> None:
    """Test that a missing chat memory raises ChatMemoryNotFoundError."""
    _, _, _, _, service = _build_service()

    with pytest.raises(ChatMemoryNotFoundError):
        await service.get_by_session_id(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_get_by_session_id_is_scoped_to_user() -> None:
    """Test that chat memory of another user is not returned."""
    repository, _, _, _, service = _build_service()
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = _chat_memory()

    with pytest.raises(ChatMemoryNotFoundError):
        await service.get_by_session_id(TEST_USER_ID_2, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_update_memory_raises_when_dependencies_missing() -> None:
    """Test that updating without update dependencies raises an error."""
    repository, _, _, _, service = _build_service(with_dependencies=False)
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = _chat_memory()

    with pytest.raises(ChatMemoryDependenciesNotConfiguredError):
        await service.update_memory(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_update_memory_raises_when_memory_missing() -> None:
    """Test that updating a missing chat memory raises ChatMemoryNotFoundError."""
    repository, _, _, _, service = _build_service(messages=_messages(1))

    with pytest.raises(ChatMemoryNotFoundError):
        await service.update_memory(TEST_USER_ID, TEST_SESSION_ID)

    assert repository.updated_memory is None


@pytest.mark.asyncio
async def test_update_memory_returns_unchanged_when_no_context() -> None:
    """Test that update is a no-op when there are no new context messages."""
    repository, _, extractor, summarizer, service = _build_service(messages=[])
    memory = _chat_memory()
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    result = await service.update_memory(TEST_USER_ID, TEST_SESSION_ID)

    assert result is memory
    assert repository.updated_memory is None
    assert extractor.call_kwargs is None
    assert summarizer.called is False


@pytest.mark.asyncio
async def test_update_memory_extracts_facts_without_summarizing() -> None:
    """Test that facts are extracted but no summary is produced below the limit."""
    repository, messages_repository, extractor, summarizer, service = _build_service(
        messages=_messages(1),
        extractor=FakeExtractor(facts=[{"key": "city", "value": "Berlin"}]),
    )
    memory = _chat_memory(
        summary="Old summary",
        facts=[{"key": "name", "value": "Alex"}],
        last_summarized_message_id=TEST_LAST_MESSAGE_ID,
    )
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    result = await service.update_memory(TEST_USER_ID, TEST_SESSION_ID)

    assert result is memory
    assert repository.updated_memory is memory
    assert memory.facts == [{"key": "city", "value": "Berlin"}]
    assert memory.summary == "Old summary"
    assert summarizer.called is False

    assert extractor.call_kwargs is not None
    assert extractor.call_kwargs["facts"] == [{"key": "name", "value": "Alex"}]
    assert all(
        isinstance(message, LLMMessage)
        for message in extractor.call_kwargs["context_messages"]
    )

    assert messages_repository.call_kwargs == {
        "user_id": TEST_USER_ID,
        "session_id": TEST_SESSION_ID,
        "message_id": TEST_LAST_MESSAGE_ID,
        "limit": settings.llm_context_messages_limit,
    }


@pytest.mark.asyncio
async def test_update_memory_summarizes_when_context_reaches_limit() -> None:
    """Test that the summary is updated when context reaches the configured limit."""
    repository, _, _, summarizer, service = _build_service(
        messages=_messages(settings.llm_context_messages_limit),
        summarizer=FakeSummarizer(summary="Fresh summary"),
    )
    memory = _chat_memory(summary="Old summary")
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    result = await service.update_memory(TEST_USER_ID, TEST_SESSION_ID)

    assert result is memory
    assert summarizer.called is True
    assert memory.summary == "Fresh summary"

    assert summarizer.call_kwargs is not None
    assert summarizer.call_kwargs["summary"] == "Old summary"
