"""Tests for chat memory service."""

from typing import cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import ChatMemory
from ai_notes_api.exceptions import ChatMemoryNotFoundError
from ai_notes_api.repositories.chat_memory import ChatMemoryRepository
from ai_notes_api.schemas import ChatMemoryUpdateSchema
from ai_notes_api.services import ChatMemoryService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MEMORY_ID = UUID("33333333-3333-3333-3333-333333333333")


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


def _build_service() -> tuple[FakeChatMemoryRepository, ChatMemoryService]:
    """Build a chat memory service wired with a fake repository.

    Returns:
        tuple[FakeChatMemoryRepository, ChatMemoryService]: Repository and service.
    """
    repository = FakeChatMemoryRepository()
    service = ChatMemoryService(
        repository=cast(ChatMemoryRepository, repository),
    )

    return repository, service


def _chat_memory(
    *,
    summary: str = "Existing summary",
    facts: list[dict[str, object]] | None = None,
) -> ChatMemory:
    """Return a chat memory model instance for service tests.

    Args:
        summary (str): Chat memory summary.
        facts (list[dict[str, object]] | None): Structured chat memory facts.

    Returns:
        ChatMemory: Chat memory model instance.
    """
    return ChatMemory(
        id=TEST_MEMORY_ID,
        session_id=TEST_SESSION_ID,
        summary=summary,
        facts=facts if facts is not None else [{"key": "name", "value": "Alex"}],
    )


@pytest.mark.asyncio
async def test_get_by_session_id_returns_memory() -> None:
    """Test that an accessible chat memory is returned."""
    repository, service = _build_service()
    memory = _chat_memory()
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    result = await service.get_by_session_id(TEST_USER_ID, TEST_SESSION_ID)

    assert result is memory


@pytest.mark.asyncio
async def test_get_by_session_id_raises_when_missing() -> None:
    """Test that a missing chat memory raises ChatMemoryNotFoundError."""
    _, service = _build_service()

    with pytest.raises(ChatMemoryNotFoundError):
        await service.get_by_session_id(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_get_by_session_id_is_scoped_to_user() -> None:
    """Test that chat memory of another user is not returned."""
    repository, service = _build_service()
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = _chat_memory()

    with pytest.raises(ChatMemoryNotFoundError):
        await service.get_by_session_id(TEST_USER_ID_2, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_update_memory_updates_fields() -> None:
    """Test that update applies new summary and facts and persists the memory."""
    repository, service = _build_service()
    memory = _chat_memory(summary="Old summary")
    repository.memories[(TEST_USER_ID, TEST_SESSION_ID)] = memory

    data = ChatMemoryUpdateSchema(
        summary="New summary",
        facts=[{"key": "city", "value": "Berlin"}],
    )

    result = await service.update_memory(TEST_USER_ID, TEST_SESSION_ID, data)

    assert result.summary == "New summary"
    assert result.facts == [{"key": "city", "value": "Berlin"}]
    assert repository.updated_memory is memory


@pytest.mark.asyncio
async def test_update_memory_raises_when_missing() -> None:
    """Test that updating a missing chat memory raises ChatMemoryNotFoundError."""
    repository, service = _build_service()

    data = ChatMemoryUpdateSchema(summary="New summary", facts=[])

    with pytest.raises(ChatMemoryNotFoundError):
        await service.update_memory(TEST_USER_ID, TEST_SESSION_ID, data)

    assert repository.updated_memory is None
