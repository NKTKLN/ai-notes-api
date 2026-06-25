"""Document processing job service module.

This module provides business logic for managing document processing jobs:
enqueuing new jobs, tracking their lifecycle, and recording their terminal
status as the worker processes the associated document.
"""

from datetime import UTC, datetime
from uuid import UUID

from ai_notes_api.db.models import DocumentProcessingJob, DocumentProcessingJobStatus
from ai_notes_api.exceptions import DocumentProcessingJobNotFoundError
from ai_notes_api.repositories import DocumentProcessingJobRepository


class DocumentProcessingJobService:
    """Service for document-processing-job-related business operations.

    Args:
        processing_repository (DocumentProcessingJobRepository): Repository used
            to perform document processing job database operations.
    """

    ERROR_MAX_LENGTH = 10_000

    def __init__(
        self,
        processing_repository: DocumentProcessingJobRepository,
    ) -> None:
        """Initialize the document processing job service.

        Args:
            processing_repository (DocumentProcessingJobRepository): Document
                processing job repository used by the service.
        """
        self.processing_jobs = processing_repository

    async def create_job(self, document_id: UUID) -> DocumentProcessingJob:
        """Create a queued document processing job for a document.

        Args:
            document_id (UUID): Unique identifier of the document to process.

        Returns:
            DocumentProcessingJob: Created document processing job.
        """
        processing_job = DocumentProcessingJob(
            document_id=document_id,
            status=DocumentProcessingJobStatus.QUEUED,
        )

        return await self.processing_jobs.create(processing_job)

    async def get_by_id(self, job_id: UUID) -> DocumentProcessingJob:
        """Return a document processing job by its identifier.

        Args:
            job_id (UUID): Unique document processing job identifier.

        Returns:
            DocumentProcessingJob: Matching document processing job.

        Raises:
            DocumentProcessingJobNotFoundError: If no document processing job with
                the given identifier exists.
        """
        processing_job = await self.processing_jobs.get_by_id(job_id)

        if processing_job is None:
            raise DocumentProcessingJobNotFoundError()

        return processing_job

    async def set_job_running(self, job_id: UUID) -> DocumentProcessingJob:
        """Mark a document processing job as running and record its start time.

        Args:
            job_id (UUID): Unique document processing job identifier.

        Returns:
            DocumentProcessingJob: Updated document processing job.

        Raises:
            DocumentProcessingJobNotFoundError: If no document processing job exists.
        """
        processing_job = await self.get_by_id(job_id)

        processing_job.status = DocumentProcessingJobStatus.RUNNING
        processing_job.started_at = datetime.now(UTC)

        return await self.processing_jobs.update(processing_job)

    async def set_job_failed(
        self, job_id: UUID, error_message: str | None = None
    ) -> DocumentProcessingJob:
        """Mark a document processing job as failed, record the error and finish time.

        Args:
            job_id (UUID): Unique document processing job identifier.
            error_message (str | None): Error message describing the failure.

        Returns:
            DocumentProcessingJob: Updated document processing job.

        Raises:
            DocumentProcessingJobNotFoundError: If no document processing job exists.
        """
        processing_job = await self.get_by_id(job_id)

        processing_job.status = DocumentProcessingJobStatus.FAILED
        processing_job.error = error_message[: self.ERROR_MAX_LENGTH]
        processing_job.finished_at = datetime.now(UTC)

        return await self.processing_jobs.update(processing_job)

    async def set_job_completed(self, job_id: UUID) -> DocumentProcessingJob:
        """Mark a document processing job as completed and record its finish time.

        Args:
            job_id (UUID): Unique document processing job identifier.

        Returns:
            DocumentProcessingJob: Updated document processing job.

        Raises:
            DocumentProcessingJobNotFoundError: If no document processing job exists.
        """
        processing_job = await self.get_by_id(job_id)

        processing_job.status = DocumentProcessingJobStatus.COMPLETED
        processing_job.finished_at = datetime.now(UTC)

        return await self.processing_jobs.update(processing_job)
