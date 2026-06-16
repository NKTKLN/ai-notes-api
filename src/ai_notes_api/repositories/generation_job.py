"""Generation job repository module.

This module provides a repository for creating, reading, and updating LLM
generation jobs in the database.
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import ChatSession, GenerationJob
from ai_notes_api.repositories.base import BaseRepository
from ai_notes_api.repositories.filters import GenerationJobListFilters


class GenerationJobRepository(BaseRepository):
    """Repository for generation job database operations."""

    async def create(self, generation_job: GenerationJob) -> GenerationJob:
        """Create a generation job in the database.

        Args:
            generation_job (GenerationJob): Generation job instance to persist.

        Returns:
            GenerationJob: Persisted generation job with refreshed
            database-generated fields.
        """
        self.session.add(generation_job)

        await self.session.flush()
        await self.session.refresh(generation_job)

        logger.info("Generation job created: id={}", generation_job.id)

        return generation_job

    async def get_by_id(self, job_id: UUID) -> GenerationJob | None:
        """Return a generation job by its identifier.

        Args:
            job_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob | None: Matching generation job if found; otherwise, None.
        """
        stmt = select(GenerationJob).where(GenerationJob.id == job_id)

        result = await self.session.execute(stmt)
        generation_job = result.scalar_one_or_none()

        if generation_job is None:
            logger.debug("Generation job not found: id={}", job_id)
        else:
            logger.debug("Generation job found: id={}", job_id)

        return generation_job

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        job_id: UUID,
    ) -> GenerationJob | None:
        """Return a user's generation job by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the generation job.
            job_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob | None: Matching generation job if found; otherwise, None.
        """
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.user_id == user_id)
            .where(GenerationJob.id == job_id)
        )

        result = await self.session.execute(stmt)
        generation_job = result.scalar_one_or_none()

        if generation_job is None:
            logger.debug("Generation job not found: id={}", job_id)
        else:
            logger.debug("Generation job found: id={}", job_id)

        return generation_job

    async def get_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: GenerationJobListFilters,
    ) -> list[GenerationJob]:
        """Return a paginated list of generation jobs.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            filters (GenerationJobListFilters): Filters used to narrow the result set.

        Returns:
            list[GenerationJob]: List of matching generation jobs ordered by
            creation date in descending order.
        """
        stmt = (
            select(GenerationJob)
            .join(ChatSession, ChatSession.id == GenerationJob.session_id)
            .where(ChatSession.user_id == user_id)
            .where(GenerationJob.session_id == session_id)
        )

        if filters.status is not None:
            stmt = stmt.where(GenerationJob.status == filters.status)

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                search_value = f"%{search}%"
                stmt = stmt.where(GenerationJob.input_message.ilike(search_value))

        stmt = (
            stmt.order_by(GenerationJob.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )

        result = await self.session.execute(stmt)
        generation_jobs = list(result.scalars().all())

        logger.debug(
            (
                "Generation jobs list fetched: count={}, user_id={}, session_id={}, "
                "limit={}, offset={}, status={}, search={}"
            ),
            len(generation_jobs),
            user_id,
            session_id,
            filters.limit,
            filters.offset,
            filters.status,
            filters.search,
        )

        return generation_jobs

    async def update(self, generation_job: GenerationJob) -> GenerationJob:
        """Update an existing generation job in the database.

        Args:
            generation_job (GenerationJob): Generation job instance with updated
                field values.

        Returns:
            GenerationJob: Updated and refreshed generation job instance.
        """
        await self.session.flush()
        await self.session.refresh(generation_job)

        logger.info("Generation job updated: id={}", generation_job.id)

        return generation_job
