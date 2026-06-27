"""LLM context builder module.

This module assembles LLM prompt messages from recent chat history and the
document chunks retrieved through semantic search.
"""

from typing import Any
from uuid import UUID

from ai_notes_api.core import settings
from ai_notes_api.db.models import DocumentChunk
from ai_notes_api.llm.embeddings import EmbeddingClient
from ai_notes_api.llm.schemas import LLMMessage
from ai_notes_api.memory import PromptBuilder
from ai_notes_api.rag.prompt_builder import RAGPromptBuilder
from ai_notes_api.services.chat_memory import ChatMemoryService
from ai_notes_api.services.document_chunk import DocumentChunkService
from ai_notes_api.services.message import MessageService


class LLMContextBuilder:
    """Builder that assembles LLM prompt messages with retrieval context.

    Args:
        embeddings (EmbeddingClient): Embedding client used to embed questions
            for document chunk retrieval.
        message_service (MessageService): Message service used to load recent
            chat history.
        chunk_service (DocumentChunkService): Document chunk service used to
            retrieve grounding context via vector search.
        memory_service (ChatMemoryService): Chat memory service used to load
            long-term memory facts and summary for personalization.
    """

    def __init__(
        self,
        embeddings: EmbeddingClient,
        message_service: MessageService,
        chunk_service: DocumentChunkService,
        memory_service: ChatMemoryService,
    ) -> None:
        """Initialize the LLM context builder.

        Args:
            embeddings (EmbeddingClient): Embedding client used by the builder.
            message_service (MessageService): Message service used by the builder.
            chunk_service (DocumentChunkService): Document chunk service used by
                the builder.
            memory_service (ChatMemoryService): Chat memory service used by the
                builder.
        """
        self.embeddings = embeddings
        self.messages = message_service
        self.chunks = chunk_service
        self.memories = memory_service

    async def _get_context_messages(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[LLMMessage]:
        """Get LLM context messages for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user.
            session_id (UUID): Unique identifier of the chat session.

        Returns:
            list[LLMMessage]: Context messages converted to the LLM message format.
        """
        raw_messages = await self.messages.get_context_messages(
            user_id=user_id,
            session_id=session_id,
            limit=settings.llm_context_messages_limit,
        )

        return [
            LLMMessage(role=message.role, content=message.content)
            for message in raw_messages
        ]

    async def _retrieve_chunks(
        self,
        user_id: UUID,
        session_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Retrieve the most similar document chunks for a query embedding.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chunks.
            session_id (UUID): Unique chat session identifier.
            query_embedding (list[float]): Query vector embedding to compare
                chunk embeddings against.
            top_k (int): Maximum number of chunks to return. Defaults to 5.

        Returns:
            list[DocumentChunk]: Matching non-deleted document chunks ordered by
            cosine distance to the query embedding in ascending order.
        """
        return await self.chunks.vector_search(
            user_id=user_id,
            session_id=session_id,
            query_embedding=query_embedding,
            top_k=top_k,
        )

    async def build(
        self,
        user_id: UUID,
        session_id: UUID,
        question: str,
    ) -> list[dict[str, Any]]:
        """Build LLM input messages with conversation and retrieval context.

        Args:
            user_id (UUID): Unique identifier of the user requesting the response.
            session_id (UUID): Unique chat session identifier.
            question (str): User question used to embed and retrieve relevant
                document chunks.

        Returns:
            list[dict[str, Any]]: Serialized LLM input messages combining
            long-term memory context and retrieved document chunks.
        """
        context_messages = await self._get_context_messages(
            user_id=user_id,
            session_id=session_id,
        )

        question_embedding = await self.embeddings.create_embedding([question])

        retrieved_chunks = await self._retrieve_chunks(
            user_id=user_id,
            session_id=session_id,
            query_embedding=question_embedding[0],
        )

        memory = await self.memories.get_by_session_id(
            user_id=user_id,
            session_id=session_id,
        )

        memory_data = PromptBuilder.build(
            context_messages,
            facts=memory.facts,
            summary=memory.summary,
        )
        rag_data = RAGPromptBuilder.build(question, retrieved_chunks)

        return [*memory_data, *rag_data]
