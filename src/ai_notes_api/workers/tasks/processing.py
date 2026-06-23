"""Document processing worker tasks module.

This module defines Celery tasks used to run queued document processing jobs.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import DocumentProcessingJobStatus
from ai_notes_api.db.session import worker_session
from ai_notes_api.exceptions.document_processing_job import (
    DocumentProcessingJobNotFoundError,
)
from ai_notes_api.integrations import openai_client
from ai_notes_api.llm import EmbeddingClient
from ai_notes_api.repositories import (
    DocumentChunkRepository,
    DocumentProcessingJobRepository,
    DocumentRepository,
)
from ai_notes_api.services import DocumentProcessingService
from ai_notes_api.storage import DocumentStorage, get_s3_client
from ai_notes_api.workers.celery_app import celery_app

ERROR_MAX_LENGTH = 10_000


@celery_app.task(name="document.process")
def run_document_processing_job(job_id: str) -> None:
    """Run a queued document processing job.

    Args:
        job_id (str): Unique document processing job identifier.
    """
    asyncio.run(_run_document_processing_job(UUID(job_id)))


async def _run_document_processing_job(job_id: UUID) -> None:
    """Run a queued document processing job asynchronously.

    Args:
        job_id (UUID): Unique document processing job identifier.

    Raises:
        DocumentProcessingJobNotFoundError: If no document processing job with
            the given identifier exists.
    """
    embeddings = EmbeddingClient(openai_client)

    async with (
        worker_session() as session,
        asynccontextmanager(get_s3_client)() as s3_client,
    ):
        processing_job_repository = DocumentProcessingJobRepository(session)
        document_repository = DocumentRepository(session)
        chunk_repository = DocumentChunkRepository(session)

        storage = DocumentStorage(s3_client)

        processing_job = await processing_job_repository.get_by_id(job_id)

        if processing_job is None:
            raise DocumentProcessingJobNotFoundError()

        document_processing = DocumentProcessingService(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            storage=storage,
            embeddings=embeddings,
        )

        try:
            logger.info("Document processing job started: id={}", job_id)

            processing_job.status = DocumentProcessingJobStatus.RUNNING
            processing_job.started_at = datetime.now(UTC)
            processing_job = await processing_job_repository.update(processing_job)

            document_processing.process_document(processing_job.document_id)

            processing_job.status = DocumentProcessingJobStatus.COMPLETED
            processing_job.finished_at = datetime.now(UTC)
            await processing_job_repository.update(processing_job)

            await session.commit()

            logger.info("Document processing job finished: id={}", job_id)

        except Exception as exc:
            await session.rollback()

            logger.exception("Document processing job failed: id={}", job_id)

            await _mark_job_failed(
                session=session,
                job_repository=processing_job_repository,
                job_id=job_id,
                error=str(exc),
            )

            raise


async def _mark_job_failed(
    session: AsyncSession,
    job_repository: DocumentProcessingJobRepository,
    job_id: UUID,
    error: str,
) -> None:
    """Mark a document processing job as failed.

    This is invoked after the job transaction has been rolled back, so it runs
    in a fresh transaction to persist the failure state.

    Args:
        session (AsyncSession): Database session used to commit the failure state.
        job_repository (DocumentProcessingJobRepository): Repository used to
            update the processing job.
        job_id (UUID): Unique document processing job identifier.
        error (str): Error message describing the failure.
    """
    processing_job = await job_repository.get_by_id(job_id)

    if processing_job is None:
        return

    processing_job.status = DocumentProcessingJobStatus.FAILED
    processing_job.error = error[:ERROR_MAX_LENGTH]
    processing_job.finished_at = datetime.now(UTC)

    await job_repository.update(processing_job)

    await session.commit()
