"""Tests for chat session service."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import ChatSession
from ai_notes_api.exceptions import ChatSessionNotFoundError
from ai_notes_api.repositories import ChatSessionListFilters
from ai_notes_api.repositories.chat_session import ChatSessionRepository
from ai_notes_api.schemas import (
    ChatSessionCreateSchema,
    ChatSessionListQuerySchema,
    ChatSessionUpdateSchema,
)
from ai_notes_api.services import ChatSessionService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_SESSION_ID_2 = UUID("33333333-3333-3333-3333-333333333333")
TEST_SESSION_ID_3 = UUID("55555555-5555-5555-5555-555555555555")


class FakeChatSessionRepository:
    """Fake chat session repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.chat_sessions: dict[UUID, ChatSession] = {}
        self.created_chat_session: ChatSession | None = None

    async def create(self, chat_session: ChatSession) -> ChatSession:
        """Create chat session."""
        chat_session.id = TEST_SESSION_ID
        self.created_chat_session = chat_session
        self.chat_sessions[chat_session.id] = chat_session
        return chat_session

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatSession | None:
        """Return chat session by id."""
        chat_session = self.chat_sessions.get(session_id)

        if (
            chat_session is not None
            and chat_session.user_id == user_id
            and chat_session.deleted_at is None
        ):
            return chat_session

        return None

    async def get_list(
        self,
        user_id: UUID,
        filters: ChatSessionListFilters,
    ) -> list[ChatSession]:
        """Return filtered chat sessions."""
        chat_sessions = [
            chat_session
            for chat_session in self.chat_sessions.values()
            if chat_session.user_id == user_id and chat_session.deleted_at is None
        ]

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                chat_sessions = [
                    chat_session
                    for chat_session in chat_sessions
                    if search in chat_session.title.strip()
                ]

        return chat_sessions[filters.offset : filters.offset + filters.limit]

    async def update(self, chat_session: ChatSession) -> ChatSession:
        """Update chat session."""
        self.chat_sessions[chat_session.id] = chat_session
        return chat_session

    async def soft_delete(self, chat_session: ChatSession) -> None:
        """Soft-delete chat session."""
        stored_chat_session = self.chat_sessions.get(chat_session.id)

        if stored_chat_session is None:
            raise ChatSessionNotFoundError()

        stored_chat_session.deleted_at = datetime.now(UTC)


@pytest.mark.asyncio
async def test_create_chat_session_success() -> None:
    """Test successful chat session creation."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    data = ChatSessionCreateSchema(title="Test session")

    chat_session = await service.create_chat_session(TEST_USER_ID, data)

    assert chat_session.id == TEST_SESSION_ID
    assert chat_session.user_id == TEST_USER_ID
    assert chat_session.title == "Test session"


@pytest.mark.asyncio
async def test_get_chat_session_success() -> None:
    """Test successful chat session retrieval by identifier."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Test session",
    )

    chat_session = await service.get_chat_session(TEST_USER_ID, TEST_SESSION_ID)

    assert chat_session.title == "Test session"


@pytest.mark.asyncio
async def test_get_chat_session_not_found_by_id() -> None:
    """Test that retrieval raises an error when chat session is not found."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_chat_session(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_get_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be retrieved."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Test session",
    )

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_chat_session(TEST_USER_ID_2, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_update_chat_session_success() -> None:
    """Test successful chat session update."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Old session",
    )

    data = ChatSessionUpdateSchema(title="New session")

    chat_session = await service.update_chat_session(
        TEST_USER_ID, TEST_SESSION_ID, data
    )

    assert chat_session.title == "New session"


@pytest.mark.asyncio
async def test_update_chat_session_not_found_by_id() -> None:
    """Test that update raises an error when chat session is not found."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    data = ChatSessionUpdateSchema(title="New session")

    with pytest.raises(ChatSessionNotFoundError):
        await service.update_chat_session(TEST_USER_ID, uuid4(), data)


@pytest.mark.asyncio
async def test_update_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be updated."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Old session",
    )

    data = ChatSessionUpdateSchema(title="New session")

    with pytest.raises(ChatSessionNotFoundError):
        await service.update_chat_session(TEST_USER_ID_2, TEST_SESSION_ID, data)


@pytest.mark.asyncio
async def test_delete_chat_session_success() -> None:
    """Test successful chat session deletion."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Test session",
    )

    await service.delete_chat_session(TEST_USER_ID, TEST_SESSION_ID)

    assert repository.chat_sessions[TEST_SESSION_ID].deleted_at is not None


@pytest.mark.asyncio
async def test_delete_chat_session_not_found_by_id() -> None:
    """Test that delete raises an error when chat session is not found."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    with pytest.raises(ChatSessionNotFoundError):
        await service.delete_chat_session(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_delete_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be deleted."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="Test session",
    )

    with pytest.raises(ChatSessionNotFoundError):
        await service.delete_chat_session(TEST_USER_ID_2, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_get_chat_sessions_list_success() -> None:
    """Test successful chat session list retrieval with filters."""
    repository = FakeChatSessionRepository()
    service = ChatSessionService(repository=cast(ChatSessionRepository, repository))

    repository.chat_sessions[TEST_SESSION_ID] = ChatSession(
        id=TEST_SESSION_ID,
        user_id=TEST_USER_ID,
        title="First Test Session",
    )

    repository.chat_sessions[TEST_SESSION_ID_2] = ChatSession(
        id=TEST_SESSION_ID_2,
        user_id=TEST_USER_ID,
        title="Second Session",
    )

    repository.chat_sessions[TEST_SESSION_ID_3] = ChatSession(
        id=TEST_SESSION_ID_3,
        user_id=TEST_USER_ID_2,
        title="First Test Session",
    )

    data = ChatSessionListQuerySchema(
        limit=1,
        search="Test",
    )

    chat_sessions = await service.get_chat_sessions_list(TEST_USER_ID, data)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].title == "First Test Session"
    assert chat_sessions[0].user_id == TEST_USER_ID
