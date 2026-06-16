"""Tests for chat session service."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import (
    ChatMemory,
    ChatSession,
    ChatSessionGenerationStatus,
)
from ai_notes_api.exceptions import (
    ChatSessionNotFoundError,
    GenerationInProgressError,
    GenerationNotFoundError,
)
from ai_notes_api.repositories import ChatSessionListFilters
from ai_notes_api.repositories.chat_memory import ChatMemoryRepository
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
TEST_GENERATION_ID = UUID("66666666-6666-6666-6666-666666666666")
TEST_GENERATION_ID_2 = UUID("77777777-7777-7777-7777-777777777777")


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

    async def acquire_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> bool:
        """Acquire a generation lock for an idle chat session."""
        chat_session = self.chat_sessions.get(session_id)

        if (
            chat_session is None
            or chat_session.user_id != user_id
            or chat_session.deleted_at is not None
            or chat_session.generation_status != ChatSessionGenerationStatus.IDLE
        ):
            return False

        chat_session.generation_status = ChatSessionGenerationStatus.RUNNING
        chat_session.generation_id = generation_id
        chat_session.generation_started_at = datetime.now(UTC)

        return True

    async def release_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Release a generation lock held by the given generation."""
        chat_session = self.chat_sessions.get(session_id)

        if (
            chat_session is None
            or chat_session.user_id != user_id
            or chat_session.deleted_at is not None
            or chat_session.generation_id != generation_id
        ):
            return

        chat_session.generation_status = ChatSessionGenerationStatus.IDLE
        chat_session.generation_id = None
        chat_session.generation_started_at = None

    async def has_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> bool:
        """Return whether a generation job owns the chat session lock."""
        chat_session = self.chat_sessions.get(session_id)

        return (
            chat_session is not None
            and chat_session.user_id == user_id
            and chat_session.deleted_at is None
            and chat_session.generation_id == generation_id
            and chat_session.generation_status == ChatSessionGenerationStatus.RUNNING
        )


class FakeChatMemoryRepository:
    """Fake chat memory repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.chat_memories: dict[UUID, ChatMemory] = {}
        self.created_chat_memory: ChatMemory | None = None

    async def create(self, chat_memory: ChatMemory) -> ChatMemory:
        """Create chat memory."""
        self.created_chat_memory = chat_memory
        self.chat_memories[chat_memory.session_id] = chat_memory
        return chat_memory


def make_service(
    repository: FakeChatSessionRepository,
    memory_repository: FakeChatMemoryRepository | None = None,
) -> ChatSessionService:
    """Build a chat session service backed by fake repositories."""
    memory_repository = memory_repository or FakeChatMemoryRepository()

    return ChatSessionService(
        session_repository=cast(ChatSessionRepository, repository),
        memory_repository=cast(ChatMemoryRepository, memory_repository),
    )


@pytest.mark.asyncio
async def test_create_chat_session_success() -> None:
    """Test successful chat session creation."""
    repository = FakeChatSessionRepository()
    memory_repository = FakeChatMemoryRepository()
    service = make_service(repository, memory_repository)

    data = ChatSessionCreateSchema(title="Test session")

    chat_session = await service.create_chat_session(TEST_USER_ID, data)

    assert chat_session.id == TEST_SESSION_ID
    assert chat_session.user_id == TEST_USER_ID
    assert chat_session.title == "Test session"
    assert memory_repository.created_chat_memory is not None
    assert memory_repository.created_chat_memory.session_id == TEST_SESSION_ID


@pytest.mark.asyncio
async def test_get_chat_session_success() -> None:
    """Test successful chat session retrieval by identifier."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

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
    service = make_service(repository)

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_chat_session(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_get_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be retrieved."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

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
    service = make_service(repository)

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
    service = make_service(repository)

    data = ChatSessionUpdateSchema(title="New session")

    with pytest.raises(ChatSessionNotFoundError):
        await service.update_chat_session(TEST_USER_ID, uuid4(), data)


@pytest.mark.asyncio
async def test_update_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be updated."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

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
    service = make_service(repository)

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
    service = make_service(repository)

    with pytest.raises(ChatSessionNotFoundError):
        await service.delete_chat_session(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_delete_chat_session_not_found_for_another_user() -> None:
    """Test that another user's chat session cannot be deleted."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

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
    service = make_service(repository)

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


def _store_chat_session(
    repository: FakeChatSessionRepository,
    *,
    session_id: UUID = TEST_SESSION_ID,
    user_id: UUID = TEST_USER_ID,
    generation_status: ChatSessionGenerationStatus = ChatSessionGenerationStatus.IDLE,
    generation_id: UUID | None = None,
) -> ChatSession:
    """Persist a chat session with explicit generation lock state."""
    chat_session = ChatSession(
        id=session_id,
        user_id=user_id,
        title="Test session",
        generation_status=generation_status,
        generation_id=generation_id,
    )

    repository.chat_sessions[session_id] = chat_session

    return chat_session


@pytest.mark.asyncio
async def test_acquire_generation_lock_success() -> None:
    """Test that the service acquires a generation lock on an idle session."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(repository)

    await service.acquire_generation_lock(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        generation_id=TEST_GENERATION_ID,
    )

    stored = repository.chat_sessions[TEST_SESSION_ID]

    assert stored.generation_status == ChatSessionGenerationStatus.RUNNING
    assert stored.generation_id == TEST_GENERATION_ID


@pytest.mark.asyncio
async def test_acquire_generation_lock_raises_when_in_progress() -> None:
    """Test that acquiring a lock raises when a generation is already running."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    with pytest.raises(GenerationInProgressError):
        await service.acquire_generation_lock(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            generation_id=TEST_GENERATION_ID_2,
        )

    assert repository.chat_sessions[TEST_SESSION_ID].generation_id == TEST_GENERATION_ID


@pytest.mark.asyncio
async def test_release_generation_lock_success() -> None:
    """Test that the service releases a generation lock it owns."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    await service.release_generation_lock(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        generation_id=TEST_GENERATION_ID,
    )

    stored = repository.chat_sessions[TEST_SESSION_ID]

    assert stored.generation_status == ChatSessionGenerationStatus.IDLE
    assert stored.generation_id is None


@pytest.mark.asyncio
async def test_release_generation_lock_other_generation_is_noop() -> None:
    """Test that releasing with a non-owning generation does not unlock."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    await service.release_generation_lock(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        generation_id=TEST_GENERATION_ID_2,
    )

    stored = repository.chat_sessions[TEST_SESSION_ID]

    assert stored.generation_status == ChatSessionGenerationStatus.RUNNING
    assert stored.generation_id == TEST_GENERATION_ID


@pytest.mark.asyncio
async def test_ensure_session_owner_success() -> None:
    """Test that ensure_session_owner passes for the owning user."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(repository)

    await service.ensure_session_owner(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_ensure_session_owner_not_found() -> None:
    """Test that ensure_session_owner raises when the session is missing."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    with pytest.raises(ChatSessionNotFoundError):
        await service.ensure_session_owner(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_ensure_session_owner_other_user() -> None:
    """Test that ensure_session_owner raises for a non-owning user."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(repository)

    with pytest.raises(ChatSessionNotFoundError):
        await service.ensure_session_owner(TEST_USER_ID_2, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_ensure_no_active_job_success() -> None:
    """Test that ensure_no_active_job passes for an idle chat session."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(repository)

    await service.ensure_no_active_job(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_ensure_no_active_job_raises_when_running() -> None:
    """Test that ensure_no_active_job raises when a generation is running."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    with pytest.raises(GenerationInProgressError):
        await service.ensure_no_active_job(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_ensure_generation_lock_owner_success() -> None:
    """Test that ensure_generation_lock_owner passes for the owning generation."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    await service.ensure_generation_lock_owner(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        generation_id=TEST_GENERATION_ID,
    )


@pytest.mark.asyncio
async def test_ensure_generation_lock_owner_raises_for_other_generation() -> None:
    """Test that ensure_generation_lock_owner raises for a non-owning generation."""
    repository = FakeChatSessionRepository()
    service = make_service(repository)

    _store_chat_session(
        repository,
        generation_status=ChatSessionGenerationStatus.RUNNING,
        generation_id=TEST_GENERATION_ID,
    )

    with pytest.raises(GenerationNotFoundError):
        await service.ensure_generation_lock_owner(
            user_id=TEST_USER_ID,
            session_id=TEST_SESSION_ID,
            generation_id=TEST_GENERATION_ID_2,
        )
