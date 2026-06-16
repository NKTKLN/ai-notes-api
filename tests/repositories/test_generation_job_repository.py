"""Tests for generation job repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import (
        ChatSession,
        GenerationJob,
        GenerationJobStatus,
        User,
    )
except ImportError:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.generation_job import (
        GenerationJob,
        GenerationJobStatus,
    )
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories import GenerationJobListFilters
from ai_notes_api.repositories.generation_job import GenerationJobRepository


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
    """Persist a chat session for generation job repository tests.

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


def create_generation_job(
    *,
    user_id: UUID,
    session_id: UUID,
    input_message: str = "Test input message",
    status: GenerationJobStatus = GenerationJobStatus.QUEUED,
    created_at: datetime | None = None,
) -> GenerationJob:
    """Create a generation job instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the generation job.
        session_id (UUID): Identifier of the chat session that owns the job.
        input_message (str): User input message used for generation.
        status (GenerationJobStatus): Generation job status.
        created_at (datetime | None): Optional explicit creation timestamp used to
            control generation job ordering in tests.

    Returns:
        GenerationJob: Generation job model instance.
    """
    generation_job = GenerationJob(
        user_id=user_id,
        session_id=session_id,
        input_message=input_message,
        status=status,
    )

    if created_at is not None:
        generation_job.created_at = created_at

    return generation_job


@pytest.mark.asyncio
async def test_create_generation_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation job creation."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    generation_job = create_generation_job(
        user_id=test_user.id,
        session_id=chat_session.id,
        input_message="Hello",
    )

    created_job = await repository.create(generation_job)

    assert created_job.id is not None
    assert created_job.user_id == test_user.id
    assert created_job.session_id == chat_session.id
    assert created_job.input_message == "Hello"
    assert created_job.status == GenerationJobStatus.QUEUED


@pytest.mark.asyncio
async def test_get_by_id_generation_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation job retrieval by identifier without user scope."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Hello",
        )
    )

    generation_job = await repository.get_by_id(created_job.id)

    assert generation_job is not None
    assert generation_job.id == created_job.id
    assert generation_job.input_message == "Hello"


@pytest.mark.asyncio
async def test_get_by_id_generation_job_not_found(
    async_session: AsyncSession,
) -> None:
    """Test that generation job retrieval by identifier returns None when missing."""
    repository = GenerationJobRepository(session=async_session)

    generation_job = await repository.get_by_id(uuid4())

    assert generation_job is None


@pytest.mark.asyncio
async def test_get_by_id_generation_job_is_not_scoped_to_user(
    async_session: AsyncSession,
    other_user: User,
) -> None:
    """Test that retrieval by identifier is not restricted to a single owner."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=other_user.id)

    created_job = await repository.create(
        create_generation_job(user_id=other_user.id, session_id=chat_session.id)
    )

    generation_job = await repository.get_by_id(created_job.id)

    assert generation_job is not None
    assert generation_job.id == created_job.id


@pytest.mark.asyncio
async def test_get_generation_job_for_user_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation job retrieval scoped to the owning user."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Hello",
        )
    )

    generation_job = await repository.get_by_id_for_user(test_user.id, created_job.id)

    assert generation_job is not None
    assert generation_job.id == created_job.id
    assert generation_job.input_message == "Hello"


@pytest.mark.asyncio
async def test_get_generation_job_for_user_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scoped generation job retrieval returns None when not found."""
    repository = GenerationJobRepository(session=async_session)

    generation_job = await repository.get_by_id_for_user(test_user.id, uuid4())

    assert generation_job is None


@pytest.mark.asyncio
async def test_get_generation_job_for_user_other_user_cannot_access(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a generation job by identifier."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_job = await repository.create(
        create_generation_job(user_id=test_user.id, session_id=chat_session.id)
    )

    generation_job = await repository.get_by_id_for_user(other_user.id, created_job.id)

    assert generation_job is None


@pytest.mark.asyncio
async def test_get_generation_jobs_list_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation jobs list retrieval ordered by creation date."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="First job",
            created_at=base,
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Second job",
            created_at=base + timedelta(seconds=1),
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0)

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 2
    assert jobs[0].input_message == "Second job"
    assert jobs[1].input_message == "First job"


@pytest.mark.asyncio
async def test_get_generation_jobs_list_empty_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful empty generation jobs list retrieval."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    filters = GenerationJobListFilters(limit=10, offset=0)

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert jobs == []


@pytest.mark.asyncio
async def test_get_generation_jobs_list_returns_only_user_owned_jobs(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that generation jobs list is scoped to the requested user."""
    repository = GenerationJobRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=owned_session.id,
            input_message="Owned job",
        )
    )
    await repository.create(
        create_generation_job(
            user_id=other_user.id,
            session_id=other_session.id,
            input_message="Other job",
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0)

    jobs = await repository.get_list(test_user.id, owned_session.id, filters)

    assert len(jobs) == 1
    assert jobs[0].id == owned_job.id


@pytest.mark.asyncio
async def test_get_generation_jobs_list_returns_only_requested_session(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that generation jobs list is scoped to the requested chat session."""
    repository = GenerationJobRepository(session=async_session)
    first_session = await create_chat_session(async_session, user_id=test_user.id)
    second_session = await create_chat_session(async_session, user_id=test_user.id)

    first_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=first_session.id,
            input_message="First session job",
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=second_session.id,
            input_message="Second session job",
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0)

    jobs = await repository.get_list(test_user.id, first_session.id, filters)

    assert len(jobs) == 1
    assert jobs[0].id == first_job.id


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_status_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation jobs list retrieval filtered by status."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            status=GenerationJobStatus.QUEUED,
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            status=GenerationJobStatus.COMPLETED,
        )
    )

    filters = GenerationJobListFilters(
        limit=10,
        offset=0,
        status=GenerationJobStatus.COMPLETED,
    )

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 1
    assert jobs[0].status == GenerationJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation jobs list retrieval filtered by input message."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="FastAPI question",
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Django question",
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0, search="fastapi")

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 1
    assert jobs[0].input_message == "FastAPI question"


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_search_whitespace_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with whitespace around search query."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="FastAPI question",
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Django question",
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0, search="   fastapi   ")

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 1
    assert jobs[0].input_message == "FastAPI question"


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_empty_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with empty search query."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="First job",
        )
    )
    await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Second job",
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=0, search="")

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_limit_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation jobs list retrieval with limit."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    for index in range(3):
        await repository.create(
            create_generation_job(
                user_id=test_user.id,
                session_id=chat_session.id,
                input_message=f"Job {index}",
            )
        )

    filters = GenerationJobListFilters(limit=2, offset=0)

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_get_generation_jobs_list_with_offset_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation jobs list retrieval with offset."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    first_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="First",
            created_at=base,
        )
    )
    second_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Second",
            created_at=base + timedelta(seconds=1),
        )
    )
    third_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            input_message="Third",
            created_at=base + timedelta(seconds=2),
        )
    )

    filters = GenerationJobListFilters(limit=10, offset=1)

    jobs = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(jobs) == 2
    assert jobs[0].id == second_job.id
    assert jobs[1].id == first_job.id
    assert third_job.id not in [job.id for job in jobs]


@pytest.mark.asyncio
async def test_update_generation_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful generation job update."""
    repository = GenerationJobRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    generation_job = await repository.create(
        create_generation_job(
            user_id=test_user.id,
            session_id=chat_session.id,
            status=GenerationJobStatus.QUEUED,
        )
    )

    generation_job.status = GenerationJobStatus.RUNNING

    updated_job = await repository.update(generation_job)

    assert updated_job.id == generation_job.id
    assert updated_job.status == GenerationJobStatus.RUNNING

    found_job = await repository.get_by_id(generation_job.id)

    assert found_job is not None
    assert found_job.status == GenerationJobStatus.RUNNING
