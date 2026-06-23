"""Document repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting documents in the database.
"""

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update

from ai_notes_api.db.models import Document, DocumentChunk
from ai_notes_api.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """Repository for document database operations."""

    async def create(self, document: Document) -> Document:
        """Create a document in the database.

        Args:
            document (Document): Document instance to persist.

        Returns:
            Document: Persisted document with refreshed database-generated fields.
        """
        self.session.add(document)

        await self.session.flush()
        await self.session.refresh(document)

        logger.info("Document created: id={}", document.id)

        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Return a document by its identifier.

        Args:
            document_id (UUID): Unique document identifier.

        Returns:
            Document | None: Matching document if found and not soft-deleted;
            otherwise, None.
        """
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        document = result.scalar_one_or_none()

        if document is None:
            logger.debug("Document not found: id={}", document_id)
        else:
            logger.debug("Document found: id={}", document_id)

        return document

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> Document | None:
        """Return a user's document by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the document.
            document_id (UUID): Unique document identifier.

        Returns:
            Document | None: Matching document if found and not soft-deleted;
            otherwise, None.
        """
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .where(Document.id == document_id)
            .where(Document.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        document = result.scalar_one_or_none()

        if document is None:
            logger.debug("Document not found: id={}", document_id)
        else:
            logger.debug("Document found: id={}", document_id)

        return document

    async def get_list_for_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[Document]:
        """Return a user's documents for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the documents.
            session_id (UUID): Unique chat session identifier.

        Returns:
            list[Document]: List of matching non-deleted documents ordered by
            creation date in descending order.
        """
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .where(Document.session_id == session_id)
            .where(Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )

        result = await self.session.execute(stmt)
        documents = list(result.scalars().all())

        logger.debug(
            "Documents list fetched: count={}, user_id={}, session_id={}",
            len(documents),
            user_id,
            session_id,
        )

        return documents

    async def update(self, document: Document) -> Document:
        """Update an existing document in the database.

        Args:
            document (Document): Document instance with updated field values.

        Returns:
            Document: Updated and refreshed document instance.
        """
        await self.session.flush()
        await self.session.refresh(document)

        logger.info("Document updated: id={}", document.id)

        return document

    async def soft_delete(self, document: Document) -> None:
        """Soft-delete a document.

        Sets the deletion timestamp for the given document instead of removing
        the row from the database.

        Args:
            document (Document): Document instance to soft-delete.
        """
        now = datetime.now(UTC)

        document.deleted_at = now

        await self.session.flush()

        await self.session.execute(
            update(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .where(DocumentChunk.deleted_at.is_(None))
            .values(deleted_at=now)
        )

        logger.info("Document soft-deleted: id={}", document.id)
