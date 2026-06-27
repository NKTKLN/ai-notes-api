"""Tests for document processing job repository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import (
    ChatSession,
    Document,
    DocumentProcessingJob,
    DocumentProcessingJobStatus,
    DocumentStatus,
    User,
)
from ai_notes_api.repositories.document_processing_job import (
    DocumentProcessingJobRepository,
)


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


async def create_document(
    async_session: AsyncSession,
    *,
    user_id: UUID,
) -> Document:
    """Persist a chat session and document for processing job repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the rows.
        user_id (UUID): Identifier of the user who owns the rows.

    Returns:
        Document: Persisted document instance.
    """
    chat_session = ChatSession(user_id=user_id, title="Test chat session")

    async_session.add(chat_session)
    await async_session.flush()

    document = Document(
        user_id=user_id,
        session_id=chat_session.id,
        filename="test.pdf",
        content_type="application/pdf",
        file_size=1024,
        checksum_sha256="checksum",
        storage_bucket="documents",
        storage_object_name="object",
        status=DocumentStatus.UPLOADED,
    )

    async_session.add(document)
    await async_session.flush()
    await async_session.refresh(document)

    return document


def create_job(
    *,
    document_id: UUID,
    status: DocumentProcessingJobStatus = DocumentProcessingJobStatus.QUEUED,
    created_at: datetime | None = None,
) -> DocumentProcessingJob:
    """Create a processing job instance for repository tests.

    Args:
        document_id (UUID): Identifier of the document the job belongs to.
        status (DocumentProcessingJobStatus): Processing job status.
        created_at (datetime | None): Optional explicit creation timestamp used to
            control processing job ordering in tests.

    Returns:
        DocumentProcessingJob: Processing job model instance.
    """
    processing_job = DocumentProcessingJob(
        document_id=document_id,
        status=status,
    )

    if created_at is not None:
        processing_job.created_at = created_at

    return processing_job


@pytest.mark.asyncio
async def test_create_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful processing job creation."""
    repository = DocumentProcessingJobRepository(session=async_session)
    document = await create_document(async_session, user_id=test_user.id)

    job = await repository.create(create_job(document_id=document.id))

    assert job.id is not None
    assert job.document_id == document.id
    assert job.status == DocumentProcessingJobStatus.QUEUED


@pytest.mark.asyncio
async def test_get_by_id_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful processing job retrieval by identifier."""
    repository = DocumentProcessingJobRepository(session=async_session)
    document = await create_document(async_session, user_id=test_user.id)

    created = await repository.create(create_job(document_id=document.id))

    job = await repository.get_by_id(created.id)

    assert job is not None
    assert job.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_job_not_found(async_session: AsyncSession) -> None:
    """Test that processing job retrieval by identifier returns None when missing."""
    repository = DocumentProcessingJobRepository(session=async_session)

    job = await repository.get_by_id(uuid4())

    assert job is None


@pytest.mark.asyncio
async def test_update_job_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful processing job update."""
    repository = DocumentProcessingJobRepository(session=async_session)
    document = await create_document(async_session, user_id=test_user.id)

    job = await repository.create(
        create_job(
            document_id=document.id,
            status=DocumentProcessingJobStatus.QUEUED,
        )
    )

    job.status = DocumentProcessingJobStatus.RUNNING
    job.started_at = datetime.now(UTC)

    updated = await repository.update(job)

    assert updated.status == DocumentProcessingJobStatus.RUNNING

    found = await repository.get_by_id(job.id)

    assert found is not None
    assert found.status == DocumentProcessingJobStatus.RUNNING
