"""Document processing job repository module.

This module provides a repository for creating, reading, and updating document
processing jobs in the database.
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import DocumentProcessingJob
from ai_notes_api.repositories.base import BaseRepository


class DocumentProcessingJobRepository(BaseRepository):
    """Repository for document processing job database operations."""

    async def create(
        self,
        processing_job: DocumentProcessingJob,
    ) -> DocumentProcessingJob:
        """Create a document processing job in the database.

        Args:
            processing_job (DocumentProcessingJob): Processing job instance to
                persist.

        Returns:
            DocumentProcessingJob: Persisted processing job with refreshed
            database-generated fields.
        """
        self.session.add(processing_job)

        await self.session.flush()
        await self.session.refresh(processing_job)

        logger.info("Document processing job created: id={}", processing_job.id)

        return processing_job

    async def get_by_id(self, job_id: UUID) -> DocumentProcessingJob | None:
        """Return a document processing job by its identifier.

        Args:
            job_id (UUID): Unique processing job identifier.

        Returns:
            DocumentProcessingJob | None: Matching processing job if found;
            otherwise, None.
        """
        stmt = select(DocumentProcessingJob).where(
            DocumentProcessingJob.id == job_id,
        )

        result = await self.session.execute(stmt)
        processing_job = result.scalar_one_or_none()

        if processing_job is None:
            logger.debug("Document processing job not found: id={}", job_id)
        else:
            logger.debug("Document processing job found: id={}", job_id)

        return processing_job

    async def get_list_for_document(
        self,
        document_id: UUID,
    ) -> list[DocumentProcessingJob]:
        """Return processing jobs for a document.

        Args:
            document_id (UUID): Unique document identifier.

        Returns:
            list[DocumentProcessingJob]: List of matching processing jobs ordered
            by creation date in descending order.
        """
        stmt = (
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == document_id)
            .order_by(DocumentProcessingJob.created_at.desc())
        )

        result = await self.session.execute(stmt)
        processing_jobs = list(result.scalars().all())

        logger.debug(
            "Document processing jobs list fetched: count={}, document_id={}",
            len(processing_jobs),
            document_id,
        )

        return processing_jobs

    async def update(
        self,
        processing_job: DocumentProcessingJob,
    ) -> DocumentProcessingJob:
        """Update an existing document processing job in the database.

        Args:
            processing_job (DocumentProcessingJob): Processing job instance with
                updated field values.

        Returns:
            DocumentProcessingJob: Updated and refreshed processing job instance.
        """
        await self.session.flush()
        await self.session.refresh(processing_job)

        logger.info("Document processing job updated: id={}", processing_job.id)

        return processing_job
