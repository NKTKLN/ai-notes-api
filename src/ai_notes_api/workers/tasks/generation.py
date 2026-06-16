"""Generation worker tasks module.

This module defines Celery tasks used to run queued LLM generation jobs.
"""

import asyncio
from uuid import UUID

from loguru import logger

from ai_notes_api.db.session import async_session_factory
from ai_notes_api.exceptions.generation_job import GenerationNotFoundError
from ai_notes_api.repositories import (
    ChatSessionRepository,
    GenerationJobRepository,
    MessageRepository,
)
from ai_notes_api.schemas.message import UserMessageCreateSchema
from ai_notes_api.services import ChatSessionService, LLMService, MessageService
from ai_notes_api.workers.celery_app import celery_app
from ai_notes_api.workers.runtime import runtime


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
        GenerationNotFoundError: If no generation job with the given identifier
            exists.
    """
    llm_client = runtime.get_llm_client()

    async with async_session_factory() as session:
        messages_repository = MessageRepository(session)
        sessions_repository = ChatSessionRepository(session)
        generation_job_repository = GenerationJobRepository(session)

        messages_service = MessageService(
            messages_repository,
            sessions_repository,
        )
        sessions_service = ChatSessionService(sessions_repository)

        generation_job = await generation_job_repository.get_by_id(job_id)

        if generation_job is None:
            raise GenerationNotFoundError()

        message = UserMessageCreateSchema(
            session_id=generation_job.session_id,
            content=generation_job.input_message,
        )

        service = LLMService(
            client=llm_client,
            sessions=sessions_service,
            messages=messages_service,
        )

        try:
            logger.info("Generation job started: id={}", job_id)

            await service.generate_job_response(
                user_id=generation_job.user_id,
                generation_id=generation_job.id,
                message=message,
            )

            await session.commit()

            logger.info("Generation job finished: id={}", job_id)

        except Exception:
            await session.rollback()

            logger.exception("Generation job failed: id={}", job_id)

            raise
