"""Tests for generation job service."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import GenerationJob, GenerationJobStatus
from ai_notes_api.exceptions import (
    ChatSessionNotFoundError,
    GenerationInProgressError,
    GenerationNotFoundError,
)
from ai_notes_api.repositories import GenerationJobListFilters
from ai_notes_api.repositories.generation_job import GenerationJobRepository
from ai_notes_api.schemas import (
    GenerationJobCreateSchema,
    GenerationJobUpdateSchema,
)
from ai_notes_api.services import ChatSessionService
from ai_notes_api.services.generation_job import JobService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_SESSION_ID_2 = UUID("33333333-3333-3333-3333-333333333333")
TEST_JOB_ID = UUID("55555555-5555-5555-5555-555555555555")


class FakeChatSessionService:
    """Fake chat session service used for testing job service behavior."""

    def __init__(self) -> None:
        """Initialize fake chat session service."""
        # Maps session id to the user that owns it.
        self.owners: dict[UUID, UUID] = {}
        # Sessions that currently hold an active generation lock.
        self.locked_sessions: set[UUID] = set()
        self.acquired_locks: list[tuple[UUID, UUID, UUID]] = []

    async def ensure_session_owner(self, user_id: UUID, session_id: UUID) -> None:
        """Ensure a chat session belongs to a user."""
        if self.owners.get(session_id) != user_id:
            raise ChatSessionNotFoundError()

    async def acquire_generation_lock(
        self,
        user_id: UUID,
        session_id: UUID,
        generation_id: UUID,
    ) -> None:
        """Acquire a generation lock for a chat session."""
        if session_id in self.locked_sessions:
            raise GenerationInProgressError()

        self.locked_sessions.add(session_id)
        self.acquired_locks.append((user_id, session_id, generation_id))


class FakeGenerationJobRepository:
    """Fake generation job repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.jobs: dict[UUID, GenerationJob] = {}
        self.created_job: GenerationJob | None = None
        self.updated_job: GenerationJob | None = None

    async def create(self, generation_job: GenerationJob) -> GenerationJob:
        """Create generation job."""
        if generation_job.id is None:
            generation_job.id = TEST_JOB_ID

        self.created_job = generation_job
        self.jobs[generation_job.id] = generation_job

        return generation_job

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        job_id: UUID,
    ) -> GenerationJob | None:
        """Return generation job scoped to the owning user."""
        generation_job = self.jobs.get(job_id)

        if generation_job is not None and generation_job.user_id == user_id:
            return generation_job

        return None

    async def get_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: GenerationJobListFilters,
    ) -> list[GenerationJob]:
        """Return filtered generation jobs for a user and session."""
        jobs = [
            job
            for job in self.jobs.values()
            if job.user_id == user_id and job.session_id == session_id
        ]

        if filters.status is not None:
            jobs = [job for job in jobs if job.status == filters.status]

        if filters.search is not None:
            search = filters.search.strip().lower()

            if search:
                jobs = [job for job in jobs if search in job.input_message.lower()]

        return jobs[filters.offset : filters.offset + filters.limit]

    async def update(self, generation_job: GenerationJob) -> GenerationJob:
        """Update generation job."""
        self.updated_job = generation_job
        self.jobs[generation_job.id] = generation_job

        return generation_job


def build_service(
    repository: FakeGenerationJobRepository,
    sessions: FakeChatSessionService,
) -> JobService:
    """Build a JobService wired with fake dependencies."""
    return JobService(
        job_repository=cast(GenerationJobRepository, repository),
        sessions=cast(ChatSessionService, sessions),
    )


def store_job(
    repository: FakeGenerationJobRepository,
    *,
    job_id: UUID = TEST_JOB_ID,
    session_id: UUID = TEST_SESSION_ID,
    input_message: str = "Test input message",
    status: GenerationJobStatus = GenerationJobStatus.QUEUED,
) -> GenerationJob:
    """Persist a generation job owned by ``TEST_USER_ID`` into the fake repository."""
    generation_job = GenerationJob(
        id=job_id,
        user_id=TEST_USER_ID,
        session_id=session_id,
        input_message=input_message,
        status=status,
    )

    repository.jobs[job_id] = generation_job

    return generation_job


@pytest.mark.asyncio
async def test_create_job_success() -> None:
    """Test successful generation job creation and lock acquisition."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(repository, sessions)

    data = GenerationJobCreateSchema(session_id=TEST_SESSION_ID, message="Hello")

    generation_job = await service.create_job(TEST_USER_ID, data)

    assert generation_job.user_id == TEST_USER_ID
    assert generation_job.session_id == TEST_SESSION_ID
    assert generation_job.input_message == "Hello"
    assert generation_job.status == GenerationJobStatus.QUEUED
    assert repository.created_job is generation_job
    assert sessions.acquired_locks == [
        (TEST_USER_ID, TEST_SESSION_ID, generation_job.id)
    ]


@pytest.mark.asyncio
async def test_create_job_session_not_owned() -> None:
    """Test that creating a job for a non-owned session raises an error."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    service = build_service(repository, sessions)

    data = GenerationJobCreateSchema(session_id=TEST_SESSION_ID, message="Hello")

    with pytest.raises(ChatSessionNotFoundError):
        await service.create_job(TEST_USER_ID_2, data)

    assert repository.created_job is None


@pytest.mark.asyncio
async def test_create_job_generation_in_progress() -> None:
    """Test that creating a job raises when a generation is already in progress."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    sessions.locked_sessions.add(TEST_SESSION_ID)
    service = build_service(repository, sessions)

    data = GenerationJobCreateSchema(session_id=TEST_SESSION_ID, message="Hello")

    with pytest.raises(GenerationInProgressError):
        await service.create_job(TEST_USER_ID, data)


@pytest.mark.asyncio
async def test_get_by_id_success() -> None:
    """Test successful generation job retrieval by identifier."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    store_job(repository, input_message="Hello")
    service = build_service(repository, sessions)

    generation_job = await service.get_by_id(TEST_USER_ID, TEST_JOB_ID)

    assert generation_job.id == TEST_JOB_ID
    assert generation_job.input_message == "Hello"


@pytest.mark.asyncio
async def test_get_by_id_not_found() -> None:
    """Test that retrieval raises an error when the job is not found."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    service = build_service(repository, sessions)

    with pytest.raises(GenerationNotFoundError):
        await service.get_by_id(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_get_by_id_not_found_for_another_user() -> None:
    """Test that another user's generation job cannot be retrieved."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    store_job(repository)
    service = build_service(repository, sessions)

    with pytest.raises(GenerationNotFoundError):
        await service.get_by_id(TEST_USER_ID_2, TEST_JOB_ID)


@pytest.mark.asyncio
async def test_get_list_success() -> None:
    """Test successful generation jobs list retrieval scoped to user and session."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    store_job(repository, job_id=uuid4(), input_message="First")
    store_job(repository, job_id=uuid4(), input_message="Second")
    store_job(
        repository,
        job_id=uuid4(),
        session_id=TEST_SESSION_ID_2,
        input_message="Other session",
    )
    service = build_service(repository, sessions)

    filters = GenerationJobListFilters(limit=10, offset=0)

    jobs = await service.get_list(TEST_USER_ID, TEST_SESSION_ID, filters)

    assert len(jobs) == 2
    assert {job.input_message for job in jobs} == {"First", "Second"}


@pytest.mark.asyncio
async def test_get_list_with_status_filter() -> None:
    """Test generation jobs list retrieval filtered by status."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    sessions.owners[TEST_SESSION_ID] = TEST_USER_ID
    store_job(repository, job_id=uuid4(), status=GenerationJobStatus.QUEUED)
    store_job(repository, job_id=uuid4(), status=GenerationJobStatus.COMPLETED)
    service = build_service(repository, sessions)

    filters = GenerationJobListFilters(
        limit=10,
        offset=0,
        status=GenerationJobStatus.COMPLETED,
    )

    jobs = await service.get_list(TEST_USER_ID, TEST_SESSION_ID, filters)

    assert len(jobs) == 1
    assert jobs[0].status == GenerationJobStatus.COMPLETED


@pytest.mark.asyncio
async def test_get_list_session_not_owned() -> None:
    """Test that listing jobs for a non-owned session raises an error."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    service = build_service(repository, sessions)

    filters = GenerationJobListFilters(limit=10, offset=0)

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_list(TEST_USER_ID, TEST_SESSION_ID, filters)


@pytest.mark.asyncio
async def test_update_job_success() -> None:
    """Test successful generation job update across multiple fields."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    store_job(repository, status=GenerationJobStatus.QUEUED)
    service = build_service(repository, sessions)

    output_message_id = uuid4()
    finished_at = datetime.now(UTC)

    data = GenerationJobUpdateSchema(
        status=GenerationJobStatus.COMPLETED,
        output_message_id=output_message_id,
        finished_at=finished_at,
    )

    generation_job = await service.update_job(TEST_USER_ID, TEST_JOB_ID, data)

    assert generation_job.status == GenerationJobStatus.COMPLETED
    assert generation_job.output_message_id == output_message_id
    assert generation_job.finished_at == finished_at
    assert repository.updated_job is generation_job


@pytest.mark.asyncio
async def test_update_job_only_updates_provided_fields() -> None:
    """Test that update only mutates fields explicitly provided in the schema."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    store_job(repository, input_message="Original", status=GenerationJobStatus.QUEUED)
    service = build_service(repository, sessions)

    data = GenerationJobUpdateSchema(status=GenerationJobStatus.RUNNING)

    generation_job = await service.update_job(TEST_USER_ID, TEST_JOB_ID, data)

    assert generation_job.status == GenerationJobStatus.RUNNING
    assert generation_job.input_message == "Original"
    assert generation_job.output_message_id is None


@pytest.mark.asyncio
async def test_update_job_not_found() -> None:
    """Test that update raises an error when the job is not found."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    service = build_service(repository, sessions)

    data = GenerationJobUpdateSchema(status=GenerationJobStatus.RUNNING)

    with pytest.raises(GenerationNotFoundError):
        await service.update_job(TEST_USER_ID, uuid4(), data)

    assert repository.updated_job is None


@pytest.mark.asyncio
async def test_update_job_not_found_for_another_user() -> None:
    """Test that another user's generation job cannot be updated."""
    repository = FakeGenerationJobRepository()
    sessions = FakeChatSessionService()
    store_job(repository)
    service = build_service(repository, sessions)

    data = GenerationJobUpdateSchema(status=GenerationJobStatus.RUNNING)

    with pytest.raises(GenerationNotFoundError):
        await service.update_job(TEST_USER_ID_2, TEST_JOB_ID, data)

    assert repository.updated_job is None
