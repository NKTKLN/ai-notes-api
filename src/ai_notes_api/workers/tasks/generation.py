"""Generation worker tasks module.

This module defines Celery tasks used to run queued LLM generation jobs.
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import GenerationJobStatus
from ai_notes_api.db.session import async_session_factory
from ai_notes_api.exceptions.generation_job import GenerationNotFoundError
from ai_notes_api.integrations import openai_client
from ai_notes_api.llm import LLMClient
from ai_notes_api.repositories import (
    ChatMemoryRepository,
    ChatSessionRepository,
    GenerationJobRepository,
    MessageRepository,
    NoteRepository,
)
from ai_notes_api.schemas.message import UserMessageCreateSchema
from ai_notes_api.services import (
    ChatSessionService,
    LLMService,
    MessageService,
    NoteService,
)
from ai_notes_api.workers.celery_app import celery_app

ERROR_MAX_LENGTH = 10_000


@celery_app.task(name="generation.run")
def run_generation_job(job_id: str) -> None:
    """Run a queued generation job.

    Args:
        job_id (str): Unique generation job identifier.
    """
    asyncio.run(_run_generation_job(UUID(job_id)))


async def _run_generation_job(job_id: UUID) -> None:
    """Run a queued generation job asynchronously.

    Args:
        job_id (UUID): Unique generation job identifier.

    Raises:
        GenerationNotFoundError: If no generation job with the given identifier exists.
    """
    llm_client = LLMClient(openai_client)

    async with async_session_factory() as session:
        notes_repository = NoteRepository(session=session)
        messages_repository = MessageRepository(session=session)
        sessions_repository = ChatSessionRepository(session=session)
        memories_repository = ChatMemoryRepository(session=session)
        generation_job_repository = GenerationJobRepository(session=session)

        notes_service = NoteService(repository=notes_repository)
        messages_service = MessageService(
            message_repository=messages_repository,
            session_repository=sessions_repository,
        )
        sessions_service = ChatSessionService(
            session_repository=sessions_repository,
            memory_repository=memories_repository,
        )

        generation_job = await generation_job_repository.get_by_id(job_id)

        if generation_job is None:
            raise GenerationNotFoundError()

        message = UserMessageCreateSchema(
            session_id=generation_job.session_id,
            content=generation_job.input_message,
        )

        service = LLMService(
            client=llm_client,
            note_service=notes_service,
            session_service=sessions_service,
            message_service=messages_service,
        )

        try:
            logger.info("Generation job started: id={}", job_id)

            generation_job.started_at = datetime.now(UTC)
            generation_job = await generation_job_repository.update(generation_job)

            completion = await service.generate_job_response(
                user_id=generation_job.user_id,
                generation_id=generation_job.id,
                message=message,
            )

            generation_job.output_message_id = completion.message_id
            generation_job.status = GenerationJobStatus.COMPLETED
            generation_job.finished_at = datetime.now(UTC)

            await generation_job_repository.update(generation_job)

            await session.commit()

            logger.info("Generation job finished: id={}", job_id)

        except Exception as exc:
            await session.rollback()

            logger.exception("Generation job failed: id={}", job_id)

            await _mark_job_failed(
                session=session,
                job_repository=generation_job_repository,
                sessions_service=sessions_service,
                job_id=job_id,
                error=str(exc),
            )

            raise


async def _mark_job_failed(
    session: AsyncSession,
    job_repository: GenerationJobRepository,
    sessions_service: ChatSessionService,
    job_id: UUID,
    error: str,
) -> None:
    """Mark a generation job as failed and release its session lock.

    This is invoked after the job transaction has been rolled back, so it runs
    in a fresh transaction to persist the failure state and release the chat
    session generation lock that the rolled-back transaction would otherwise
    leave held.

    Args:
        session (AsyncSession): Database session used to commit the failure state.
        job_repository (GenerationJobRepository): Repository used to update the
            generation job.
        sessions_service (ChatSessionService): Chat session service used to
            release the generation lock.
        job_id (UUID): Unique generation job identifier.
        error (str): Error message describing the failure.
    """
    generation_job = await job_repository.get_by_id(job_id)

    if generation_job is None:
        return

    generation_job.status = GenerationJobStatus.FAILED
    generation_job.error = error[:ERROR_MAX_LENGTH]
    generation_job.finished_at = datetime.now(UTC)

    await job_repository.update(generation_job)

    await sessions_service.release_generation_lock(
        user_id=generation_job.user_id,
        session_id=generation_job.session_id,
        generation_id=generation_job.id,
    )

    await session.commit()
