"""Document chunk service module.

This module provides business logic for working with document chunks.
"""

from uuid import UUID

from ai_notes_api.db.models import DocumentChunk
from ai_notes_api.repositories import DocumentChunkRepository


class DocumentChunkService:
    """Service for document chunk-related business operations.

    Args:
        chunk_repository (DocumentChunkRepository): Repository used to perform
            document chunk database operations.
    """

    def __init__(
        self,
        chunk_repository: DocumentChunkRepository,
    ) -> None:
        """Initialize the document chunk service.

        Args:
            chunk_repository (DocumentChunkRepository): Document chunk repository
                used by the service.
        """
        self.chunks = chunk_repository

    async def vector_search(
        self,
        user_id: UUID,
        session_id: UUID,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Return the most similar document chunks in a user's chat session.

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
        return await self.chunks.vector_search_in_user_session(
            query_embedding=query_embedding,
            user_id=user_id,
            session_id=session_id,
            top_k=top_k,
        )
