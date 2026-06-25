"""Tests for document processing job service."""

from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import (
    DocumentProcessingJob,
    DocumentProcessingJobStatus,
)
from ai_notes_api.exceptions import DocumentProcessingJobNotFoundError
from ai_notes_api.repositories.document_processing_job import (
    DocumentProcessingJobRepository,
)
from ai_notes_api.services.document_processing_job import DocumentProcessingJobService

TEST_DOCUMENT_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_JOB_ID = UUID("55555555-5555-5555-5555-555555555555")


class FakeDocumentProcessingJobRepository:
    """Fake document processing job repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize the fake repository."""
        self.processing_jobs: dict[UUID, DocumentProcessingJob] = {}
        self.created_job: DocumentProcessingJob | None = None
        self.updated_job: DocumentProcessingJob | None = None

    async def create(self, job: DocumentProcessingJob) -> DocumentProcessingJob:
        """Create a document processing job."""
        job.id = TEST_JOB_ID

        self.created_job = job
        self.processing_jobs[job.id] = job

        return job

    async def get_by_id(self, job_id: UUID) -> DocumentProcessingJob | None:
        """Return a document processing job by its identifier."""
        return self.processing_jobs.get(job_id)

    async def update(self, job: DocumentProcessingJob) -> DocumentProcessingJob:
        """Update a document processing job."""
        self.updated_job = job
        self.processing_jobs[job.id] = job

        return job


def build_service(
    repository: FakeDocumentProcessingJobRepository,
) -> DocumentProcessingJobService:
    """Build a DocumentProcessingJobService wired with a fake repository."""
    return DocumentProcessingJobService(
        processing_repository=cast(DocumentProcessingJobRepository, repository),
    )


def store_job(
    repository: FakeDocumentProcessingJobRepository,
    *,
    job_id: UUID = TEST_JOB_ID,
    document_id: UUID = TEST_DOCUMENT_ID,
    status: DocumentProcessingJobStatus = DocumentProcessingJobStatus.QUEUED,
) -> DocumentProcessingJob:
    """Persist a document processing job into the fake repository."""
    job = DocumentProcessingJob(
        id=job_id,
        document_id=document_id,
        status=status,
    )

    repository.processing_jobs[job_id] = job

    return job


@pytest.mark.asyncio
async def test_create_job_success() -> None:
    """Test successful document processing job creation."""
    repository = FakeDocumentProcessingJobRepository()
    service = build_service(repository)

    job = await service.create_job(TEST_DOCUMENT_ID)

    assert job.document_id == TEST_DOCUMENT_ID
    assert job.status == DocumentProcessingJobStatus.QUEUED
    assert repository.created_job is job


@pytest.mark.asyncio
async def test_get_by_id_success() -> None:
    """Test successful document processing job retrieval by identifier."""
    repository = FakeDocumentProcessingJobRepository()
    store_job(repository)
    service = build_service(repository)

    job = await service.get_by_id(TEST_JOB_ID)

    assert job.id == TEST_JOB_ID
    assert job.document_id == TEST_DOCUMENT_ID


@pytest.mark.asyncio
async def test_get_by_id_not_found() -> None:
    """Test that retrieval raises an error when the job is not found."""
    repository = FakeDocumentProcessingJobRepository()
    service = build_service(repository)

    with pytest.raises(DocumentProcessingJobNotFoundError):
        await service.get_by_id(uuid4())


@pytest.mark.asyncio
async def test_set_job_running_success() -> None:
    """Test that marking a job running sets the status and start time."""
    repository = FakeDocumentProcessingJobRepository()
    store_job(repository, status=DocumentProcessingJobStatus.QUEUED)
    service = build_service(repository)

    job = await service.set_job_running(TEST_JOB_ID)

    assert job.status == DocumentProcessingJobStatus.RUNNING
    assert job.started_at is not None
    assert repository.updated_job is job


@pytest.mark.asyncio
async def test_set_job_running_not_found() -> None:
    """Test that marking a missing job running raises an error."""
    repository = FakeDocumentProcessingJobRepository()
    service = build_service(repository)

    with pytest.raises(DocumentProcessingJobNotFoundError):
        await service.set_job_running(uuid4())

    assert repository.updated_job is None


@pytest.mark.asyncio
async def test_set_job_failed_success() -> None:
    """Test that marking a job failed sets status, error, and finish time."""
    repository = FakeDocumentProcessingJobRepository()
    store_job(repository, status=DocumentProcessingJobStatus.RUNNING)
    service = build_service(repository)

    job = await service.set_job_failed(TEST_JOB_ID, "boom")

    assert job.status == DocumentProcessingJobStatus.FAILED
    assert job.error == "boom"
    assert job.finished_at is not None
    assert repository.updated_job is job


@pytest.mark.asyncio
async def test_set_job_failed_truncates_error_message() -> None:
    """Test that a long error message is truncated to ``ERROR_MAX_LENGTH``."""
    repository = FakeDocumentProcessingJobRepository()
    store_job(repository, status=DocumentProcessingJobStatus.RUNNING)
    service = build_service(repository)

    error_message = "x" * (DocumentProcessingJobService.ERROR_MAX_LENGTH + 100)

    job = await service.set_job_failed(TEST_JOB_ID, error_message)

    assert job.error is not None
    assert len(job.error) == DocumentProcessingJobService.ERROR_MAX_LENGTH


@pytest.mark.asyncio
async def test_set_job_failed_not_found() -> None:
    """Test that marking a missing job failed raises an error."""
    repository = FakeDocumentProcessingJobRepository()
    service = build_service(repository)

    with pytest.raises(DocumentProcessingJobNotFoundError):
        await service.set_job_failed(uuid4(), "boom")

    assert repository.updated_job is None


@pytest.mark.asyncio
async def test_set_job_completed_success() -> None:
    """Test that marking a job completed sets the status and finish time."""
    repository = FakeDocumentProcessingJobRepository()
    store_job(repository, status=DocumentProcessingJobStatus.RUNNING)
    service = build_service(repository)

    job = await service.set_job_completed(TEST_JOB_ID)

    assert job.status == DocumentProcessingJobStatus.COMPLETED
    assert job.finished_at is not None
    assert repository.updated_job is job


@pytest.mark.asyncio
async def test_set_job_completed_not_found() -> None:
    """Test that marking a missing job completed raises an error."""
    repository = FakeDocumentProcessingJobRepository()
    service = build_service(repository)

    with pytest.raises(DocumentProcessingJobNotFoundError):
        await service.set_job_completed(uuid4())

    assert repository.updated_job is None
