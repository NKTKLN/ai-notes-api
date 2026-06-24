"""Document processing service module.

This module provides the business logic that turns an uploaded document into
embedded chunks: downloading the source file from object storage, extracting and
splitting its text, generating embeddings, persisting the resulting chunks, and
updating the document status accordingly.
"""

import hashlib
from io import BytesIO
from uuid import UUID

import tiktoken
from loguru import logger
from markitdown import MarkItDown, StreamInfo, UnsupportedFormatException

from ai_notes_api.core import settings
from ai_notes_api.db.models import Document, DocumentChunk, DocumentStatus
from ai_notes_api.exceptions import (
    DocumentNotFoundError,
    InvalidChunkSizeError,
    InvalidOverlapError,
    OverlapGreaterThanOrEqualChunkSizeError,
    UnsupportedDocumentFormatError,
)
from ai_notes_api.llm import EmbeddingClient
from ai_notes_api.repositories import DocumentChunkRepository, DocumentRepository
from ai_notes_api.storage import DocumentStorage


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
        self.md = MarkItDown()

    async def process_document(self, document_id: UUID) -> Document:
        """Process a document into embedded chunks.

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

            embeddings = await self.embeddings.create_embedding(text_chunks)

            chunks = []

            for chunk_index in range(len(text_chunks)):
                text_chunk = text_chunks[chunk_index]
                embedding = embeddings[chunk_index]

                chunk_hash = hashlib.sha256(text_chunk.encode())

                chunks.append(
                    DocumentChunk(
                        user_id=document.user_id,
                        session_id=document.session_id,
                        document_id=document.id,
                        chunk_index=chunk_index,
                        content=text_chunk,
                        content_hash=(chunk_hash).hexdigest(),
                        embedding=embedding,
                        embedding_model=settings.open_ai_embedding_model,
                    )
                )

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
        """Extract markdown text from raw document bytes.

        Args:
            data (bytes): Raw document content to convert.
            content_type (str): MIME type of the document.

        Returns:
            str: Extracted document text as markdown.

        Raises:
            UnsupportedDocumentFormatError: If MarkItDown does not support the
                given content type.
        """
        logger.debug(
            "Extracting text: content_type={}, size={} bytes",
            content_type,
            len(data),
        )

        try:
            result = self.md.convert_stream(
                BytesIO(data),
                stream_info=StreamInfo(mimetype=content_type),
            )

        except UnsupportedFormatException as exc:
            logger.warning("Unsupported document format: content_type={}", content_type)
            raise UnsupportedDocumentFormatError(content_type) from exc

        logger.debug(
            "Text extraction finished: content_type={}, chars={}",
            content_type,
            len(result.markdown),
        )

        return result.markdown

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[str]:
        """Split extracted text into token-based overlapping chunks.

        Args:
            text (str): Plain text to split.
            chunk_size (int): Maximum number of tokens in each chunk.
            overlap (int): Number of tokens repeated between adjacent chunks.

        Returns:
            list[str]: Ordered non-empty text chunks ready for embedding.

        Raises:
            InvalidChunkSizeError: If `chunk_size` is less than or equal to zero.
            InvalidOverlapError: If `overlap` is negative.
            OverlapGreaterThanOrEqualChunkSizeError: If `overlap` is greater than
                or equal to `chunk_size`.
        """
        if chunk_size <= 0:
            raise InvalidChunkSizeError()

        if overlap < 0:
            raise InvalidOverlapError()

        if overlap >= chunk_size:
            raise OverlapGreaterThanOrEqualChunkSizeError()

        logger.debug(
            "Chunking text: chars={}, chunk_size={}, overlap={}",
            len(text),
            chunk_size,
            overlap,
        )

        encoding = tiktoken.get_encoding(settings.tiktoken_encoding_name)

        tokens = encoding.encode(text)
        chunks = []

        step = chunk_size - overlap

        for start in range(0, len(tokens), step):
            end = start + chunk_size
            chunk_tokens = tokens[start:end]

            chunk = encoding.decode(chunk_tokens).strip()

            if chunk:
                chunks.append(chunk)

            if end >= len(tokens):
                break

        logger.debug(
            "Chunking finished: tokens={}, chunks={}",
            len(tokens),
            len(chunks),
        )

        return chunks

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
