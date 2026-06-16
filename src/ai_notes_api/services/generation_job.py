"""Generation job service module.

This module provides business logic for managing LLM generation jobs: enqueuing
new jobs, tracking their lifecycle, and enforcing the one-active-generation-per-
session invariant shared by asynchronous and streaming generation paths.
"""

from uuid import UUID

from ai_notes_api.db.models import GenerationJob, GenerationJobStatus
from ai_notes_api.exceptions import GenerationNotFoundError
from ai_notes_api.repositories import GenerationJobListFilters, GenerationJobRepository
from ai_notes_api.schemas import GenerationJobCreateSchema, GenerationJobUpdateSchema
from ai_notes_api.services.chat_session import ChatSessionService


class JobService:
    """Service for generation-job-related business operations.

    Args:
        job_repository (GenerationJobRepository): Repository used to perform
            generation job database operations.
        session_service (ChatSessionService): Chat session service used to validate
            access and manage generation locks.
    """

    def __init__(
        self,
        job_repository: GenerationJobRepository,
        session_service: ChatSessionService,
    ) -> None:
        """Initialize the generation job service.

        Args:
            job_repository (GenerationJobRepository): Generation job repository
                used by the service.
            session_service (ChatSessionService): Chat session service used by the
                service.
        """
        self.jobs = job_repository
        self.sessions = session_service

    async def create_job(
        self,
        user_id: UUID,
        data: GenerationJobCreateSchema,
    ) -> GenerationJob:
        """Create a generation job and acquire a session generation lock.

        Args:
            user_id (UUID): Unique identifier of the user creating the generation job.
            data (GenerationJobCreateSchema): Validated data used to create the
                generation job.

        Returns:
            GenerationJob: Created generation job.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
            GenerationInProgressError: If generation is already in progress.
        """
        await self.sessions.ensure_session_owner(user_id, data.session_id)

        generation_job_data = GenerationJob(
            user_id=user_id,
            session_id=data.session_id,
            input_message=data.message,
            status=GenerationJobStatus.QUEUED,
        )

        generation_job = await self.jobs.create(generation_job_data)

        await self.sessions.acquire_generation_lock(
            user_id=user_id,
            session_id=data.session_id,
            generation_id=generation_job.id,
        )

        return generation_job

    async def get_by_id(self, user_id: UUID, job_id: UUID) -> GenerationJob:
        """Return a user's generation job by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the job.
            job_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob: Matching generation job.

        Raises:
            GenerationNotFoundError: If no accessible generation job exists.
        """
        generation_job = await self.jobs.get_by_id_for_user(user_id, job_id)

        if generation_job is None:
            raise GenerationNotFoundError()

        return generation_job

    async def get_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: GenerationJobListFilters,
    ) -> list[GenerationJob]:
        """Return a paginated list of a user's generation jobs for a session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the session.
            session_id (UUID): Unique chat session identifier.
            filters (GenerationJobListFilters): Filters used to narrow results.

        Returns:
            list[GenerationJob]: Matching generation jobs.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self.sessions.ensure_session_owner(user_id, session_id)

        return await self.jobs.get_list(user_id, session_id, filters)

    async def update_job(
        self,
        user_id: UUID,
        job_id: UUID,
        data: GenerationJobUpdateSchema,
    ) -> GenerationJob:
        """Update a user's generation job.

        Args:
            user_id (UUID): Unique identifier of the user who owns the generation
                job.
            job_id (UUID): Unique generation job identifier.
            data (GenerationJobUpdateSchema): Validated data used to update the
                generation job.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no accessible generation job exists.
        """
        job = await self.get_by_id(user_id, job_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(job, field, value)

        return await self.jobs.update(job)
