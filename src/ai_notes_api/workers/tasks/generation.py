"""Generation worker tasks module.

This module defines Celery tasks used to run queued LLM generation jobs.
"""

import asyncio
from uuid import UUID

from loguru import logger

from ai_notes_api.db.session import worker_session
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
    GenerationJobService,
    LLMService,
    MessageService,
    NoteService,
)
from ai_notes_api.workers.celery_app import celery_app


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

    async with worker_session() as session:
        notes_repository = NoteRepository(session)
        messages_repository = MessageRepository(session)
        sessions_repository = ChatSessionRepository(session)
        memories_repository = ChatMemoryRepository(session)
        generation_repository = GenerationJobRepository(session)

        notes_service = NoteService(notes_repository)
        messages_service = MessageService(
            message_repository=messages_repository,
            session_repository=sessions_repository,
        )
        sessions_service = ChatSessionService(
            session_repository=sessions_repository,
            memory_repository=memories_repository,
        )
        generation_service = GenerationJobService(
            generation_repository=generation_repository
        )

        generation = await generation_service.get_by_id(job_id)

        message = UserMessageCreateSchema(
            session_id=generation.session_id,
            content=generation.input_message,
        )

        service = LLMService(
            client=llm_client,
            note_service=notes_service,
            session_service=sessions_service,
            message_service=messages_service,
        )

        try:
            logger.info("Generation job started: id={}", generation.id)

            await generation_service.set_job_running(generation.id)

            completion = await service.generate_job_response(
                user_id=generation.user_id,
                generation_id=generation.id,
                message=message,
            )

            await generation_service.set_job_completed(
                generation_id=generation.id,
                message_id=completion.message_id,
            )

            await session.commit()

            logger.info("Generation job finished: id={}", job_id)

        except Exception as exc:
            await session.rollback()

            logger.exception("Generation job failed: id={}", job_id)

            await generation_service.set_job_failed(
                generation_id=generation.id,
                error_message=str(exc),
            )

            await sessions_service.release_generation_lock(
                user_id=generation.user_id,
                session_id=generation.session_id,
                generation_id=generation.id,
            )

            await session.commit()

            raise
