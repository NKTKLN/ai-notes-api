"""Document processing worker tasks module.

This module defines Celery tasks used to run queued document processing jobs.
"""

import asyncio
from contextlib import asynccontextmanager
from uuid import UUID

from loguru import logger

from ai_notes_api.db.session import worker_session
from ai_notes_api.ingestion import TextExtractor, TokenTextChunker
from ai_notes_api.integrations import openai_client
from ai_notes_api.llm import EmbeddingClient
from ai_notes_api.repositories import (
    DocumentChunkRepository,
    DocumentProcessingJobRepository,
    DocumentRepository,
)
from ai_notes_api.services import (
    DocumentProcessingJobService,
    DocumentProcessingService,
)
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
        processing_repository = DocumentProcessingJobRepository(session)
        document_repository = DocumentRepository(session)
        chunk_repository = DocumentChunkRepository(session)

        processing_jobs = DocumentProcessingJobService(processing_repository)

        storage = DocumentStorage(s3_client)

        text_extractor = TextExtractor()
        chunker = TokenTextChunker()

        processing_job = await processing_jobs.get_by_id(job_id)

        document_processing = DocumentProcessingService(
            document_repository=document_repository,
            chunk_repository=chunk_repository,
            storage=storage,
            embeddings=embeddings,
            text_extractor=text_extractor,
            chunker=chunker,
        )

        try:
            logger.info("Document processing job started: id={}", job_id)

            await processing_jobs.set_job_running(processing_job.id)

            await document_processing.process_document(processing_job.document_id)

            await processing_jobs.set_job_completed(processing_job.id)

            await session.commit()

            logger.info("Document processing job finished: id={}", job_id)

        except Exception as exc:
            await session.rollback()

            logger.exception("Document processing job failed: id={}", job_id)

            await processing_jobs.set_job_failed(
                job_id=processing_job.id,
                error_message=str(exc),
            )

            await session.commit()

            raise
