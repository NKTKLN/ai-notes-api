"""Memory worker tasks module.

This module defines Celery tasks used to update chat memory from recent chat
messages.
"""

import asyncio
from uuid import UUID

from loguru import logger

from ai_notes_api.db.session import worker_session
from ai_notes_api.integrations import openai_client
from ai_notes_api.memory import MemoryExtractor, MemorySummarizer
from ai_notes_api.repositories import ChatMemoryRepository, MessageRepository
from ai_notes_api.services import ChatMemoryService
from ai_notes_api.workers.celery_app import celery_app


@celery_app.task(name="memory.update")
def update_chat_memory_summary(user_id: str, session_id: str) -> None:
    """Run a queued chat memory update job.

    Args:
        user_id (str): Unique user identifier.
        session_id (str): Unique chat session identifier.
    """
    asyncio.run(_update_chat_memory_summary(UUID(user_id), UUID(session_id)))


async def _update_chat_memory_summary(user_id: UUID, session_id: UUID) -> None:
    """Update chat memory summary asynchronously.

    Args:
        user_id (UUID): Unique identifier of the user who owns the chat session.
        session_id (UUID): Unique chat session identifier.

    Raises:
        ChatMemoryNotFoundError: If no chat memory exists for the given chat
            session identifier.
        MemoryInProgressError: If chat memory summarization is already in progress.
    """
    extractor = MemoryExtractor(openai_client)
    summarizer = MemorySummarizer(openai_client)

    async with worker_session() as session:
        messages_repository = MessageRepository(session)
        memories_repository = ChatMemoryRepository(session)

        memory = ChatMemoryService(
            messages_repository=messages_repository,
            memories_repository=memories_repository,
            extractor=extractor,
            summarizer=summarizer,
        )

        try:
            logger.info("Memory update job started: session_id={}", session_id)

            await memory.update_memory(user_id, session_id)
            await session.commit()

            logger.info("Memory update job finished: session_id={}", session_id)

        except Exception:
            await session.rollback()

            logger.exception("Memory update job failed: session_id={}", session_id)

            raise
