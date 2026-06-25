"""Generation job service module.

This module provides business logic for managing LLM generation jobs: enqueuing
new jobs, tracking their lifecycle, and enforcing the one-active-generation-per-
session invariant shared by asynchronous and streaming generation paths.
"""

from datetime import UTC, datetime
from uuid import UUID

from ai_notes_api.db.models import GenerationJob, GenerationJobStatus
from ai_notes_api.exceptions import GenerationNotFoundError
from ai_notes_api.repositories import GenerationJobListFilters, GenerationJobRepository
from ai_notes_api.schemas import GenerationJobCreateSchema, GenerationJobUpdateSchema
from ai_notes_api.services.chat_session import ChatSessionService


class GenerationJobService:
    """Service for generation-job-related business operations.

    Args:
        job_repository (GenerationJobRepository): Repository used to perform
            generation job database operations.
        session_service (ChatSessionService): Chat session service used to validate
            access and manage generation locks.
    """

    ERROR_MAX_LENGTH = 10_000

    def __init__(
        self,
        generation_repository: GenerationJobRepository,
        session_service: ChatSessionService,
    ) -> None:
        """Initialize the generation job service.

        Args:
            generation_repository (GenerationJobRepository): Generation job repository
                used by the service.
            session_service (ChatSessionService): Chat session service used by the
                service.
        """
        self.generations = generation_repository
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

        generation_data = GenerationJob(
            user_id=user_id,
            session_id=data.session_id,
            input_message=data.message,
            status=GenerationJobStatus.QUEUED,
        )

        generation_job = await self.generations.create(generation_data)

        await self.sessions.acquire_generation_lock(
            user_id=user_id,
            session_id=data.session_id,
            generation_id=generation_job.id,
        )

        return generation_job

    async def get_by_id(self, job_id: UUID) -> GenerationJob:
        """Return generation job by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the job.
            job_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob: Matching generation job.

        Raises:
            GenerationNotFoundError: If no accessible generation job exists.
        """
        generation_job = await self.generations.get_by_id(job_id)

        if generation_job is None:
            raise GenerationNotFoundError()

        return generation_job

    async def get_by_id_for_user(self, user_id: UUID, job_id: UUID) -> GenerationJob:
        """Return a user's generation job by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the job.
            job_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob: Matching generation job.

        Raises:
            GenerationNotFoundError: If no accessible generation job exists.
        """
        generation_job = await self.generations.get_by_id_for_user(
            user_id=user_id,
            job_id=job_id,
        )

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

        return await self.generations.get_list(user_id, session_id, filters)

    async def update_job(
        self,
        user_id: UUID,
        job_id: UUID,
        data: GenerationJobUpdateSchema,
    ) -> GenerationJob:
        """Update a user's generation job.

        Args:
            user_id (UUID): Unique identifier of the user who owns the generation job.
            job_id (UUID): Unique generation job identifier.
            data (GenerationJobUpdateSchema): Validated data used to update the
                generation job.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no accessible generation job exists.
        """
        generation_job = await self.get_by_id_for_user(user_id, job_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                setattr(generation_job, field, value)

        return await self.generations.update(generation_job)

    async def set_job_running(self, generation_id: UUID) -> GenerationJob:
        """Mark a generation job as running and record its start time.

        Args:
            generation_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no generation job exists.
        """
        generation_job = await self.get_by_id(generation_id)

        generation_job.status = GenerationJobStatus.RUNNING
        generation_job.started_at = datetime.now(UTC)

        return await self.generations.update(generation_job)

    async def set_job_failed(
        self, generation_id: UUID, error_message: str | None = None
    ) -> GenerationJob:
        """Mark a generation job as failed and record the error and finish time.

        The error message is truncated to ``ERROR_MAX_LENGTH`` characters.

        Args:
            generation_id (UUID): Unique generation job identifier.
            error_message (str | None): Error message describing the failure.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no generation job exists.
        """
        generation_job = await self.get_by_id(generation_id)

        generation_job.status = GenerationJobStatus.FAILED
        generation_job.error = error_message[: self.ERROR_MAX_LENGTH]
        generation_job.finished_at = datetime.now(UTC)

        return await self.generations.update(generation_job)

    async def set_job_completed(
        self, generation_id: UUID, message_id: UUID
    ) -> GenerationJob:
        """Mark a generation job as completed and link its output message.

        Args:
            generation_id (UUID): Unique generation job identifier.
            message_id (UUID): Unique identifier of the generated output message.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no generation job exists.
        """
        generation_job = await self.get_by_id(generation_id)

        generation_job.status = GenerationJobStatus.COMPLETED
        generation_job.output_message_id = message_id
        generation_job.finished_at = datetime.now(UTC)

        return await self.generations.update(generation_job)

    async def set_job_cancelled(self, generation_id: UUID) -> GenerationJob:
        """Mark a generation job as cancelled and record its finish time.

        Args:
            generation_id (UUID): Unique generation job identifier.

        Returns:
            GenerationJob: Updated generation job.

        Raises:
            GenerationNotFoundError: If no generation job exists.
        """
        generation_job = await self.get_by_id(generation_id)

        generation_job.status = GenerationJobStatus.CANCELLED
        generation_job.finished_at = datetime.now(UTC)

        return await self.generations.update(generation_job)
