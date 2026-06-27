"""Generation worker tasks module.

This module defines Celery tasks used to run queued LLM generation jobs.
"""

import asyncio
from uuid import UUID

from loguru import logger

from ai_notes_api.db.session import worker_session
from ai_notes_api.exceptions import GenerationMessageMissingError
from ai_notes_api.integrations import openai_client
from ai_notes_api.llm import EmbeddingClient, LLMClient
from ai_notes_api.repositories import (
    ChatMemoryRepository,
    ChatSessionRepository,
    DocumentChunkRepository,
    GenerationJobRepository,
    MessageRepository,
    NoteRepository,
)
from ai_notes_api.schemas.completion import ChatCompletionResponseSchema
from ai_notes_api.schemas.message import UserMessageCreateSchema
from ai_notes_api.services import (
    ChatMemoryService,
    ChatSessionService,
    DocumentChunkService,
    GenerationJobService,
    LLMContextBuilder,
    LLMService,
    MessageService,
    NoteService,
)
from ai_notes_api.workers.celery_app import celery_app


def _require_message_id(completion: ChatCompletionResponseSchema) -> UUID:
    """Return the persisted message id of a completion or raise if missing.

    Args:
        completion (ChatCompletionResponseSchema): Completion produced by the LLM
            service.

    Returns:
        UUID: Identifier of the persisted assistant message.

    Raises:
        GenerationMessageMissingError: If the completion has no persisted message id.
    """
    if completion.message_id is None:
        raise GenerationMessageMissingError()

    return completion.message_id


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
    embeddings = EmbeddingClient(openai_client)

    async with worker_session() as session:
        notes_repository = NoteRepository(session)
        messages_repository = MessageRepository(session)
        sessions_repository = ChatSessionRepository(session)
        memories_repository = ChatMemoryRepository(session)
        generation_repository = GenerationJobRepository(session)
        chunks_repository = DocumentChunkRepository(session)

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
            generation_repository=generation_repository,
            session_service=sessions_service,
        )
        chunks_service = DocumentChunkService(chunk_repository=chunks_repository)
        memory_service = ChatMemoryService(memories_repository=memories_repository)
        context_builder = LLMContextBuilder(
            embeddings=embeddings,
            message_service=messages_service,
            chunk_service=chunks_service,
            memory_service=memory_service,
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
            context_builder=context_builder,
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
                message_id=_require_message_id(completion),
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
