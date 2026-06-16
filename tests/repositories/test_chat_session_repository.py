"""Tests for chat session repository."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import (
        ChatSession,
        GenerationJob,
        GenerationJobStatus,
        Message,
        User,
    )
except ImportError:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.generation_job import (
        GenerationJob,
        GenerationJobStatus,
    )
    from ai_notes_api.db.models.message import Message
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories import ChatSessionListFilters
from ai_notes_api.repositories.chat_session import ChatSessionRepository


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


def create_chat_session(
    *,
    user_id: UUID,
    title: str = "Test chat session",
) -> ChatSession:
    """Create a chat session instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the chat session.
        title (str): Chat session title.

    Returns:
        ChatSession: Chat session model instance.
    """
    return ChatSession(
        user_id=user_id,
        title=title,
    )


def _message_role_value(role: str) -> object:
    """Return a message role value compatible with either str or Enum columns."""
    try:
        enum_class = Message.role.property.columns[0].type.enum_class
    except AttributeError:
        return role

    if enum_class is None:
        return role

    try:
        return enum_class(role)
    except ValueError:
        return getattr(enum_class, role.upper())


def create_message(
    *,
    session_id: UUID,
    content: str = "Test message",
    role: str = "user",
) -> Message:
    """Create a message instance for repository tests.

    Args:
        session_id (UUID): Identifier of the chat session that owns the message.
        content (str): Message content.
        role (str): Message role.

    Returns:
        Message: Message model instance.
    """
    return Message(
        session_id=session_id,
        role=_message_role_value(role),
        content=content,
    )


def create_generation_job(
    *,
    user_id: UUID,
    session_id: UUID,
    input_message: str = "Test input message",
    status: GenerationJobStatus = GenerationJobStatus.QUEUED,
) -> GenerationJob:
    """Create a generation job instance for chat session repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the generation job.
        session_id (UUID): Identifier of the chat session that owns the job.
        input_message (str): User input message used for generation.
        status (GenerationJobStatus): Generation job status.

    Returns:
        GenerationJob: Generation job model instance.
    """
    return GenerationJob(
        user_id=user_id,
        session_id=session_id,
        input_message=input_message,
        status=status,
    )


@pytest.mark.asyncio
async def test_create_chat_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat session creation."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = create_chat_session(
        user_id=test_user.id,
        title="Test session",
    )

    created_chat_session = await repository.create(chat_session)

    assert created_chat_session.id is not None
    assert created_chat_session.user_id == test_user.id
    assert created_chat_session.title == "Test session"
    assert created_chat_session.deleted_at is None


@pytest.mark.asyncio
async def test_get_by_id_chat_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat session retrieval by identifier without user scope."""
    repository = ChatSessionRepository(session=async_session)

    created_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    chat_session = await repository.get_by_id(created_chat_session.id)

    assert chat_session is not None
    assert chat_session.id == created_chat_session.id
    assert chat_session.user_id == test_user.id
    assert chat_session.title == "Test session"
    assert chat_session.deleted_at is None


@pytest.mark.asyncio
async def test_get_by_id_chat_session_not_found(
    async_session: AsyncSession,
) -> None:
    """Test that chat session retrieval by identifier returns None when missing."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.get_by_id(uuid4())

    assert chat_session is None


@pytest.mark.asyncio
async def test_get_by_id_chat_session_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that retrieval by identifier returns None for a soft-deleted session."""
    repository = ChatSessionRepository(session=async_session)

    created_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )

    await repository.soft_delete(created_chat_session)

    chat_session = await repository.get_by_id(created_chat_session.id)

    assert chat_session is None


@pytest.mark.asyncio
async def test_get_by_id_chat_session_is_not_scoped_to_user(
    async_session: AsyncSession,
    other_user: User,
) -> None:
    """Test that retrieval by identifier is not restricted to a single owner."""
    repository = ChatSessionRepository(session=async_session)

    other_chat_session = await repository.create(
        create_chat_session(
            user_id=other_user.id,
            title="Other session",
        )
    )

    chat_session = await repository.get_by_id(other_chat_session.id)

    assert chat_session is not None
    assert chat_session.id == other_chat_session.id
    assert chat_session.user_id == other_user.id


@pytest.mark.asyncio
async def test_get_chat_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat session retrieval by identifier."""
    repository = ChatSessionRepository(session=async_session)

    created_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    chat_session = await repository.get_by_id_for_user(
        test_user.id,
        created_chat_session.id,
    )

    assert chat_session is not None
    assert chat_session.id == created_chat_session.id
    assert chat_session.user_id == test_user.id
    assert chat_session.title == "Test session"
    assert chat_session.deleted_at is None


@pytest.mark.asyncio
async def test_get_chat_session_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session retrieval returns None when not found."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.get_by_id_for_user(test_user.id, uuid4())

    assert chat_session is None


@pytest.mark.asyncio
async def test_get_chat_session_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft-deleted chat session retrieval returns None."""
    repository = ChatSessionRepository(session=async_session)

    created_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )

    await repository.soft_delete(created_chat_session)

    chat_session = await repository.get_by_id_for_user(
        test_user.id,
        created_chat_session.id,
    )

    assert chat_session is None


@pytest.mark.asyncio
async def test_get_chat_session_by_id_returns_only_user_owned_session(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that chat session retrieval is scoped to the owner."""
    repository = ChatSessionRepository(session=async_session)

    owned_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Owned session",
        )
    )

    other_chat_session = await repository.create(
        create_chat_session(
            user_id=other_user.id,
            title="Other session",
        )
    )

    found_chat_session = await repository.get_by_id_for_user(
        test_user.id,
        owned_chat_session.id,
    )
    forbidden_chat_session = await repository.get_by_id_for_user(
        test_user.id,
        other_chat_session.id,
    )

    assert found_chat_session is not None
    assert found_chat_session.id == owned_chat_session.id
    assert found_chat_session.user_id == test_user.id
    assert forbidden_chat_session is None


@pytest.mark.asyncio
async def test_get_chat_session_by_id_other_user_cannot_access_session(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a chat session by identifier."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Private session",
        )
    )

    found_chat_session = await repository.get_by_id_for_user(
        other_user.id,
        chat_session.id,
    )

    assert found_chat_session is None


@pytest.mark.asyncio
async def test_get_chat_sessions_list_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat sessions list retrieval."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="First session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Second session",
        )
    )

    filters = ChatSessionListFilters(limit=10, offset=0)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 2
    assert chat_sessions[0].title == "Second session"
    assert chat_sessions[1].title == "First session"
    assert all(chat_session.user_id == test_user.id for chat_session in chat_sessions)


@pytest.mark.asyncio
async def test_get_chat_sessions_list_empty_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful empty chat sessions list retrieval."""
    repository = ChatSessionRepository(session=async_session)

    filters = ChatSessionListFilters(limit=10, offset=0)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert chat_sessions == []


@pytest.mark.asyncio
async def test_get_chat_sessions_list_returns_only_user_owned_sessions(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that chat sessions list is scoped to the requested user."""
    repository = ChatSessionRepository(session=async_session)

    owned_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Owned session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=other_user.id,
            title="Other user session",
        )
    )

    filters = ChatSessionListFilters(limit=10, offset=0)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].id == owned_chat_session.id
    assert chat_sessions[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_chat_sessions_list_empty_for_user_without_sessions(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that a user without chat sessions receives an empty list."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Owned session",
        )
    )

    filters = ChatSessionListFilters(limit=10, offset=0)

    chat_sessions = await repository.get_list(other_user.id, filters)

    assert chat_sessions == []


@pytest.mark.asyncio
async def test_get_chat_sessions_list_excludes_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat sessions list excludes soft-deleted sessions."""
    repository = ChatSessionRepository(session=async_session)

    active_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Active session",
        )
    )

    deleted_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )

    await repository.soft_delete(deleted_chat_session)

    filters = ChatSessionListFilters(limit=10, offset=0)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].id == active_chat_session.id
    assert chat_sessions[0].title == "Active session"
    assert chat_sessions[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_chat_sessions_list_with_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat sessions list retrieval filtered by title search."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="FastAPI session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Django session",
        )
    )

    filters = ChatSessionListFilters(
        search="fastapi",
        limit=10,
        offset=0,
    )

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].title == "FastAPI session"
    assert chat_sessions[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_chat_sessions_list_with_search_whitespace_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with whitespace around search query."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="FastAPI session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Django session",
        )
    )

    filters = ChatSessionListFilters(
        search="   fastapi   ",
        limit=10,
        offset=0,
    )

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].title == "FastAPI session"
    assert chat_sessions[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_chat_sessions_list_with_empty_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with empty search query."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="First session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Second session",
        )
    )

    filters = ChatSessionListFilters(
        search="",
        limit=10,
        offset=0,
    )

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 2
    assert all(chat_session.user_id == test_user.id for chat_session in chat_sessions)


@pytest.mark.asyncio
async def test_get_chat_sessions_list_filters_do_not_leak_other_user_sessions(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that filters are applied only inside requested user's sessions."""
    repository = ChatSessionRepository(session=async_session)

    owned_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Matching owned session",
        )
    )

    await repository.create(
        create_chat_session(
            user_id=other_user.id,
            title="Matching other session",
        )
    )

    filters = ChatSessionListFilters(
        search="matching",
        limit=10,
        offset=0,
    )

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 1
    assert chat_sessions[0].id == owned_chat_session.id
    assert chat_sessions[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_chat_sessions_list_with_limit_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat sessions list retrieval with limit."""
    repository = ChatSessionRepository(session=async_session)

    await repository.create(create_chat_session(user_id=test_user.id, title="First"))
    await repository.create(create_chat_session(user_id=test_user.id, title="Second"))
    await repository.create(create_chat_session(user_id=test_user.id, title="Third"))

    filters = ChatSessionListFilters(limit=2, offset=0)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 2
    assert all(chat_session.user_id == test_user.id for chat_session in chat_sessions)


@pytest.mark.asyncio
async def test_get_chat_sessions_list_with_offset_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat sessions list retrieval with offset."""
    repository = ChatSessionRepository(session=async_session)

    first_chat_session = await repository.create(
        create_chat_session(user_id=test_user.id, title="First")
    )
    second_chat_session = await repository.create(
        create_chat_session(user_id=test_user.id, title="Second")
    )
    third_chat_session = await repository.create(
        create_chat_session(user_id=test_user.id, title="Third")
    )

    filters = ChatSessionListFilters(limit=10, offset=1)

    chat_sessions = await repository.get_list(test_user.id, filters)

    assert len(chat_sessions) == 2
    assert chat_sessions[0].id == second_chat_session.id
    assert chat_sessions[1].id == first_chat_session.id
    assert third_chat_session.id not in [
        chat_session.id for chat_session in chat_sessions
    ]
    assert all(chat_session.user_id == test_user.id for chat_session in chat_sessions)


@pytest.mark.asyncio
async def test_update_chat_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat session update."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Old session",
        )
    )

    chat_session.title = "New session"

    updated_chat_session = await repository.update(chat_session)

    assert updated_chat_session.id == chat_session.id
    assert updated_chat_session.user_id == test_user.id
    assert updated_chat_session.title == "New session"

    found_chat_session = await repository.get_by_id_for_user(
        test_user.id, chat_session.id
    )

    assert found_chat_session is not None
    assert found_chat_session.user_id == test_user.id
    assert found_chat_session.title == "New session"


@pytest.mark.asyncio
async def test_delete_chat_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful chat session soft deletion."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    await repository.soft_delete(chat_session)

    assert chat_session.deleted_at is not None
    assert isinstance(chat_session.deleted_at, datetime)


@pytest.mark.asyncio
async def test_delete_chat_session_soft_deletes_related_messages_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session soft deletion also soft-deletes related messages."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    first_message = create_message(
        session_id=chat_session.id,
        content="First message",
    )
    second_message = create_message(
        session_id=chat_session.id,
        content="Second message",
    )
    async_session.add_all([first_message, second_message])
    await async_session.flush()

    await repository.soft_delete(chat_session)

    result = await async_session.execute(
        select(Message).where(Message.session_id == chat_session.id)
    )
    stored_messages = list(result.scalars().all())

    assert len(stored_messages) == 2
    assert {message.id for message in stored_messages} == {
        first_message.id,
        second_message.id,
    }
    assert all(message.deleted_at is not None for message in stored_messages)
    assert all(isinstance(message.deleted_at, datetime) for message in stored_messages)


@pytest.mark.asyncio
async def test_delete_chat_session_does_not_soft_delete_other_session_messages(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session soft deletion does not affect other sessions' messages."""
    repository = ChatSessionRepository(session=async_session)

    deleted_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )
    active_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Active session",
        )
    )

    deleted_session_message = create_message(
        session_id=deleted_chat_session.id,
        content="Deleted session message",
    )
    active_session_message = create_message(
        session_id=active_chat_session.id,
        content="Active session message",
    )
    async_session.add_all([deleted_session_message, active_session_message])
    await async_session.flush()

    await repository.soft_delete(deleted_chat_session)

    deleted_message_result = await async_session.execute(
        select(Message).where(Message.id == deleted_session_message.id)
    )
    active_message_result = await async_session.execute(
        select(Message).where(Message.id == active_session_message.id)
    )
    stored_deleted_session_message = deleted_message_result.scalar_one()
    stored_active_session_message = active_message_result.scalar_one()

    assert stored_deleted_session_message.deleted_at is not None
    assert stored_active_session_message.deleted_at is None


@pytest.mark.asyncio
async def test_delete_chat_session_hides_session_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion hides chat session from repository reads."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    await repository.soft_delete(chat_session)

    found_chat_session = await repository.get_by_id_for_user(
        test_user.id, chat_session.id
    )

    assert found_chat_session is None


@pytest.mark.asyncio
async def test_get_chat_session_soft_deleted_for_owner_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that owner cannot retrieve a soft-deleted chat session."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )

    await repository.soft_delete(chat_session)

    found_chat_session = await repository.get_by_id_for_user(
        test_user.id, chat_session.id
    )

    assert found_chat_session is None


@pytest.mark.asyncio
async def test_delete_chat_session_preserves_database_row_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion preserves the database row."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    await repository.soft_delete(chat_session)

    result = await async_session.execute(
        select(ChatSession).where(ChatSession.id == chat_session.id)
    )
    stored_chat_session = result.scalar_one_or_none()

    assert stored_chat_session is not None
    assert stored_chat_session.id == chat_session.id
    assert stored_chat_session.user_id == test_user.id
    assert stored_chat_session.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_chat_session_cancels_active_generation_jobs_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session soft deletion cancels active generation jobs."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    queued_job = create_generation_job(
        user_id=test_user.id,
        session_id=chat_session.id,
        status=GenerationJobStatus.QUEUED,
    )
    running_job = create_generation_job(
        user_id=test_user.id,
        session_id=chat_session.id,
        status=GenerationJobStatus.RUNNING,
    )
    async_session.add_all([queued_job, running_job])
    await async_session.flush()

    await repository.soft_delete(chat_session)

    result = await async_session.execute(
        select(GenerationJob).where(GenerationJob.session_id == chat_session.id)
    )
    stored_jobs = list(result.scalars().all())

    assert len(stored_jobs) == 2
    assert all(job.status == GenerationJobStatus.CANCELLED for job in stored_jobs)
    assert all(job.finished_at is not None for job in stored_jobs)
    assert all(isinstance(job.finished_at, datetime) for job in stored_jobs)


@pytest.mark.asyncio
async def test_delete_chat_session_keeps_finished_generation_jobs_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session soft deletion does not touch finished jobs."""
    repository = ChatSessionRepository(session=async_session)

    chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Test session",
        )
    )

    completed_job = create_generation_job(
        user_id=test_user.id,
        session_id=chat_session.id,
        status=GenerationJobStatus.COMPLETED,
    )
    failed_job = create_generation_job(
        user_id=test_user.id,
        session_id=chat_session.id,
        status=GenerationJobStatus.FAILED,
    )
    async_session.add_all([completed_job, failed_job])
    await async_session.flush()

    await repository.soft_delete(chat_session)

    completed_result = await async_session.execute(
        select(GenerationJob).where(GenerationJob.id == completed_job.id)
    )
    failed_result = await async_session.execute(
        select(GenerationJob).where(GenerationJob.id == failed_job.id)
    )
    stored_completed_job = completed_result.scalar_one()
    stored_failed_job = failed_result.scalar_one()

    assert stored_completed_job.status == GenerationJobStatus.COMPLETED
    assert stored_failed_job.status == GenerationJobStatus.FAILED


@pytest.mark.asyncio
async def test_delete_chat_session_does_not_cancel_other_session_jobs_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that chat session soft deletion does not cancel other sessions' jobs."""
    repository = ChatSessionRepository(session=async_session)

    deleted_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Deleted session",
        )
    )
    active_chat_session = await repository.create(
        create_chat_session(
            user_id=test_user.id,
            title="Active session",
        )
    )

    deleted_session_job = create_generation_job(
        user_id=test_user.id,
        session_id=deleted_chat_session.id,
        status=GenerationJobStatus.QUEUED,
    )
    active_session_job = create_generation_job(
        user_id=test_user.id,
        session_id=active_chat_session.id,
        status=GenerationJobStatus.QUEUED,
    )
    async_session.add_all([deleted_session_job, active_session_job])
    await async_session.flush()

    await repository.soft_delete(deleted_chat_session)

    deleted_job_result = await async_session.execute(
        select(GenerationJob).where(GenerationJob.id == deleted_session_job.id)
    )
    active_job_result = await async_session.execute(
        select(GenerationJob).where(GenerationJob.id == active_session_job.id)
    )
    stored_deleted_session_job = deleted_job_result.scalar_one()
    stored_active_session_job = active_job_result.scalar_one()

    assert stored_deleted_session_job.status == GenerationJobStatus.CANCELLED
    assert stored_active_session_job.status == GenerationJobStatus.QUEUED
