"""Document chunk repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting document chunks in the database.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update

from ai_notes_api.db.models import DocumentChunk
from ai_notes_api.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository):
    """Repository for document chunk database operations."""

    async def create(self, document_chunk: DocumentChunk) -> DocumentChunk:
        """Create a document chunk in the database.

        Args:
            document_chunk (DocumentChunk): Document chunk instance to persist.

        Returns:
            DocumentChunk: Persisted document chunk with refreshed
            database-generated fields.
        """
        self.session.add(document_chunk)

        await self.session.flush()
        await self.session.refresh(document_chunk)

        logger.info("Document chunk created: id={}", document_chunk.id)

        return document_chunk

    async def create_many(
        self,
        document_chunks: Sequence[DocumentChunk],
    ) -> list[DocumentChunk]:
        """Create multiple document chunks in the database.

        Args:
            document_chunks (Sequence[DocumentChunk]): Document chunk instances to
                persist.

        Returns:
            list[DocumentChunk]: Persisted document chunks with refreshed
            database-generated fields.
        """
        document_chunks = list(document_chunks)

        self.session.add_all(document_chunks)

        await self.session.flush()

        for document_chunk in document_chunks:
            await self.session.refresh(document_chunk)

        logger.info("Document chunks created: count={}", len(document_chunks))

        return document_chunks

    async def get_by_id(self, chunk_id: UUID) -> DocumentChunk | None:
        """Return a document chunk by its identifier.

        Args:
            chunk_id (UUID): Unique document chunk identifier.

        Returns:
            DocumentChunk | None: Matching document chunk if found and not
            soft-deleted; otherwise, None.
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.id == chunk_id)
            .where(DocumentChunk.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        document_chunk = result.scalar_one_or_none()

        if document_chunk is None:
            logger.debug("Document chunk not found: id={}", chunk_id)
        else:
            logger.debug("Document chunk found: id={}", chunk_id)

        return document_chunk

    async def get_list_for_document(self, document_id: UUID) -> list[DocumentChunk]:
        """Return document chunks for a document.

        Args:
            document_id (UUID): Unique document identifier.

        Returns:
            list[DocumentChunk]: List of matching non-deleted document chunks
            ordered by chunk index in ascending order.
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.deleted_at.is_(None))
            .order_by(DocumentChunk.chunk_index.asc())
        )

        result = await self.session.execute(stmt)
        document_chunks = list(result.scalars().all())

        logger.debug(
            "Document chunks list fetched: count={}, document_id={}",
            len(document_chunks),
            document_id,
        )

        return document_chunks

    async def vector_search_in_user_session(
        self,
        query_embedding: list[float],
        user_id: UUID,
        session_id: UUID,
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Return the most similar document chunks in a user's chat session.

        Args:
            query_embedding (list[float]): Query vector embedding to compare
                chunk embeddings against.
            user_id (UUID): Unique identifier of the user who owns the chunks.
            session_id (UUID): Unique chat session identifier.
            top_k (int): Maximum number of chunks to return.

        Returns:
            list[DocumentChunk]: List of matching non-deleted document chunks
            ordered by cosine distance to the query embedding in ascending order.
        """
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.user_id == user_id)
            .where(DocumentChunk.session_id == session_id)
            .where(DocumentChunk.deleted_at.is_(None))
            .order_by(distance)
            .limit(top_k)
        )

        result = await self.session.execute(stmt)
        document_chunks = list(result.scalars().all())

        logger.debug(
            "Document chunks search completed: count={}, user_id={}, "
            "session_id={}, top_k={}",
            len(document_chunks),
            user_id,
            session_id,
            top_k,
        )

        return document_chunks

    async def update(self, document_chunk: DocumentChunk) -> DocumentChunk:
        """Update an existing document chunk in the database.

        Args:
            document_chunk (DocumentChunk): Document chunk instance with updated
                field values.

        Returns:
            DocumentChunk: Updated and refreshed document chunk instance.
        """
        await self.session.flush()
        await self.session.refresh(document_chunk)

        logger.info("Document chunk updated: id={}", document_chunk.id)

        return document_chunk

    async def soft_delete_for_document(self, document_id: UUID) -> None:
        """Soft-delete all document chunks of a document.

        Sets the deletion timestamp for every non-deleted chunk of the given
        document instead of removing rows from the database.

        Args:
            document_id (UUID): Unique document identifier.
        """
        await self.session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .where(DocumentChunk.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )

        await self.session.flush()

        logger.info("Document chunks soft-deleted: document_id={}", document_id)
