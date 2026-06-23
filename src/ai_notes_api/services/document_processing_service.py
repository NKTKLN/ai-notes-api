"""Document processing service module.

This module provides the business logic that turns an uploaded document into
embedded chunks: downloading the source file from object storage, extracting and
splitting its text, generating embeddings, persisting the resulting chunks, and
updating the document status accordingly.
"""

import hashlib
from dataclasses import dataclass
from uuid import UUID

from loguru import logger

from ai_notes_api.core import settings
from ai_notes_api.db.models import Document, DocumentChunk, DocumentStatus
from ai_notes_api.exceptions import DocumentNotFoundError
from ai_notes_api.llm import EmbeddingClient
from ai_notes_api.repositories import DocumentChunkRepository, DocumentRepository
from ai_notes_api.storage import DocumentStorage


@dataclass(slots=True)
class TextChunk:
    """Plain-text chunk produced while splitting a document.

    Attributes:
        index (int): Position of the chunk within the document.
        content (str): Text content of the chunk.
    """

    index: int
    content: str


class DocumentProcessingService:
    """Service that processes documents into embedded chunks.

    Args:
        document_repository (DocumentRepository): Repository used to load and
            update the source document.
        chunk_repository (DocumentChunkRepository): Repository used to persist
            document chunks.
        storage (DocumentStorage): Object storage helper used to download the
            source file from S3.
        embeddings (EmbeddingClient): Client used to generate chunk embeddings.
    """

    CHUNK_SIZE = 1_000
    CHUNK_OVERLAP = 200
    ERROR_MAX_LENGTH = 10_000

    def __init__(
        self,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        storage: DocumentStorage,
        embeddings: EmbeddingClient,
    ) -> None:
        """Initialize the document processing service.

        Args:
            document_repository (DocumentRepository): Document repository used by
                the service.
            chunk_repository (DocumentChunkRepository): Document chunk repository
                used by the service.
            storage (DocumentStorage): Object storage helper used by the service.
            embeddings (EmbeddingClient): Embedding client used by the service.
        """
        self.documents = document_repository
        self.chunks = chunk_repository
        self.storage = storage
        self.embeddings = embeddings

    async def process_document(self, document_id: UUID) -> Document:
        """Process a document into embedded chunks.

        Downloads the source file from object storage, extracts and splits its
        text, generates embeddings, persists the resulting chunks, and marks the
        document as ``READY``. If any step fails, the document is marked
        ``FAILED`` and the original error is re-raised.

        Args:
            document_id (UUID): Unique identifier of the document to process.

        Returns:
            Document: Processed document in its terminal status.

        Raises:
            DocumentNotFoundError: If no document with the given identifier exists.
        """
        document = await self.documents.get_by_id(document_id)

        if document is None:
            raise DocumentNotFoundError()

        try:
            logger.info("Document processing started: id={}", document_id)

            document.status = DocumentStatus.PROCESSING
            document = await self.documents.update(document)

            data = await self.storage.download_file(document.storage_object_name)

            text = await self._extract_text(data, document.content_type)
            text_chunks = self._chunk_text(text)

            embeddings = await self.embeddings.create_embedding(
                [chunk.content for chunk in text_chunks]
            )

            chunks = [
                DocumentChunk(
                    user_id=document.user_id,
                    session_id=document.session_id,
                    document_id=document.id,
                    chunk_index=text_chunk.index,
                    content=text_chunk.content,
                    content_hash=hashlib.sha256(
                        text_chunk.content.encode()
                    ).hexdigest(),
                    embedding=embedding,
                    embedding_model=settings.open_ai_embedding_model,
                )
                for text_chunk, embedding in zip(text_chunks, embeddings, strict=True)
            ]

            await self.chunks.create_many(chunks)

            document = await self._mark_ready(document)
        except Exception as exc:
            logger.exception("Document processing failed: id={}", document_id)

            await self._mark_failed(document, str(exc))

            raise
        else:
            logger.info("Document processing finished: id={}", document_id)

            return document

    async def _extract_text(self, data: bytes, content_type: str) -> str:
        """Extract plain text from raw document content.

        Args:
            data (bytes): Raw document content.
            content_type (str): MIME type of the document used to select the
                appropriate extraction strategy.

        Returns:
            str: Extracted plain text.
        """
        raise NotImplementedError

    def _chunk_text(self, text: str) -> list[TextChunk]:
        """Split extracted text into overlapping chunks.

        Args:
            text (str): Plain text to split.

        Returns:
            list[TextChunk]: Ordered text chunks ready for embedding.
        """
        raise NotImplementedError

    async def _mark_ready(self, document: Document) -> Document:
        """Mark a document as successfully processed.

        Args:
            document (Document): Document to mark as ready.

        Returns:
            Document: Updated document in the ``READY`` status.
        """
        document.status = DocumentStatus.READY
        document.error_message = None

        return await self.documents.update(document)

    async def _mark_failed(self, document: Document, error: str) -> Document:
        """Mark a document as failed.

        Args:
            document (Document): Document to mark as failed.
            error (str): Error message describing the failure.

        Returns:
            Document: Updated document in the ``FAILED`` status.
        """
        document.status = DocumentStatus.FAILED
        document.error_message = error[: self.ERROR_MAX_LENGTH]

        return await self.documents.update(document)
