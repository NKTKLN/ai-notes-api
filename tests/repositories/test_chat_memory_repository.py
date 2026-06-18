"""Tests for chat memory repository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import ChatMemory, ChatSession, User
except ImportError:
    from ai_notes_api.db.models.chat_memory import ChatMemory
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories.chat_memory import ChatMemoryRepository


@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def other_user(async_session: AsyncSession) -> User:
    """Create another test user."""
    user = User(
        email="other-user@example.com",
        username="other_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


async def create_chat_session(
    async_session: AsyncSession,
    *,
    user_id: UUID,
    title: str = "Test chat session",
) -> ChatSession:
    """Persist a chat session for chat memory repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the chat session.
        title (str): Chat session title.

    Returns:
        ChatSession: Persisted chat session instance.
    """
    chat_session = ChatSession(
        user_id=user_id,
        title=title,
    )

    async_session.add(chat_session)
    await async_session.flush()
    await async_session.refresh(chat_session)

    return chat_session


def create_chat_memory(
    *,
    session_id: UUID,
    summary: str = "Test summary",
    facts: list[dict[str, object]] | None = None,
) -> ChatMemory:
    """Create a chat memory instance for repository tests.

    Args:
        session_id (UUID): Identifier of the chat session that owns the memory.
        summary (str): Chat memory summary.
        facts (list[dict[str, object]] | None): Structured chat memory facts.

    Returns:
        ChatMemory: Chat memory model instance.
    """
    return ChatMemory(
        session_id=session_id,
        summary=summary,
        facts=facts if facts is not None else [{"key": "name", "value": "Alex"}],
    )


@pytest.mark.asyncio
async def test_create_chat_memory_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat memory creation."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_chat_memory(
            session_id=chat_session.id,
            summary="Initial summary",
        )
    )

    assert created.id is not None
    assert created.session_id == chat_session.id
    assert created.summary == "Initial summary"
    assert created.facts == [{"key": "name", "value": "Alex"}]
    assert created.created_at is not None


@pytest.mark.asyncio
async def test_get_by_session_id_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat memory retrieval by session identifier."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    created = await repository.create(create_chat_memory(session_id=chat_session.id))

    chat_memory = await repository.get_by_session_id(chat_session.id)

    assert chat_memory is not None
    assert chat_memory.id == created.id
    assert chat_memory.session_id == chat_session.id


@pytest.mark.asyncio
async def test_get_by_session_id_not_found(async_session: AsyncSession) -> None:
    """Test that retrieval by session identifier returns None when missing."""
    repository = ChatMemoryRepository(session=async_session)

    chat_memory = await repository.get_by_session_id(uuid4())

    assert chat_memory is None


@pytest.mark.asyncio
async def test_get_by_session_id_soft_deleted_session_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that retrieval returns None when the chat session is soft-deleted."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    await repository.create(create_chat_memory(session_id=chat_session.id))

    chat_session.deleted_at = datetime.now(UTC)
    await async_session.flush()

    chat_memory = await repository.get_by_session_id(chat_session.id)

    assert chat_memory is None


@pytest.mark.asyncio
async def test_get_by_session_id_for_user_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat memory retrieval scoped to the owning user."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    created = await repository.create(create_chat_memory(session_id=chat_session.id))

    chat_memory = await repository.get_by_session_id_for_user(
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    assert chat_memory is not None
    assert chat_memory.id == created.id


@pytest.mark.asyncio
async def test_get_by_session_id_for_user_wrong_user_not_found(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that retrieval is scoped to the owning user."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    await repository.create(create_chat_memory(session_id=chat_session.id))

    chat_memory = await repository.get_by_session_id_for_user(
        user_id=other_user.id,
        session_id=chat_session.id,
    )

    assert chat_memory is None


@pytest.mark.asyncio
async def test_get_by_session_id_for_user_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scoped retrieval returns None for a soft-deleted session."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    await repository.create(create_chat_memory(session_id=chat_session.id))

    chat_session.deleted_at = datetime.now(UTC)
    await async_session.flush()

    chat_memory = await repository.get_by_session_id_for_user(
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    assert chat_memory is None


@pytest.mark.asyncio
async def test_update_chat_memory_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat memory update."""
    repository = ChatMemoryRepository(session=async_session)

    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    chat_memory = await repository.create(
        create_chat_memory(
            session_id=chat_session.id,
            summary="Old summary",
        )
    )

    chat_memory.summary = "New summary"
    chat_memory.facts = [{"key": "city", "value": "Berlin"}]

    updated = await repository.update(chat_memory)

    assert updated.summary == "New summary"
    assert updated.facts == [{"key": "city", "value": "Berlin"}]

    persisted = await repository.get_by_session_id(chat_session.id)

    assert persisted is not None
    assert persisted.summary == "New summary"
    assert persisted.facts == [{"key": "city", "value": "Berlin"}]
