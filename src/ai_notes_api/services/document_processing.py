"""Document processing service module.

This module provides the business logic that turns an uploaded document into
embedded chunks: downloading the source file from object storage, extracting and
splitting its text, generating embeddings, persisting the resulting chunks, and
updating the document status accordingly.
"""

from uuid import UUID

from loguru import logger

from ai_notes_api.core import settings
from ai_notes_api.db.models import Document, DocumentChunk, DocumentStatus
from ai_notes_api.exceptions import (
    ChunkEmbeddingCountMismatchError,
    DocumentNotFoundError,
)
from ai_notes_api.ingestion import TextExtractor, TokenTextChunker
from ai_notes_api.ingestion.schemas import TextChunk
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
        text_extractor (TextExtractor): Extractor used to convert raw document
            bytes into text.
        chunker (TokenTextChunker): Chunker used to split extracted text into
            embeddable chunks.
    """

    ERROR_MAX_LENGTH = 10_000

    def __init__(  # noqa: PLR0913
        self,
        document_repository: DocumentRepository,
        chunk_repository: DocumentChunkRepository,
        storage: DocumentStorage,
        embeddings: EmbeddingClient,
        text_extractor: TextExtractor,
        chunker: TokenTextChunker,
    ) -> None:
        """Initialize the document processing service.

        Args:
            document_repository (DocumentRepository): Document repository used by
                the service.
            chunk_repository (DocumentChunkRepository): Document chunk repository
                used by the service.
            storage (DocumentStorage): Object storage helper used by the service.
            embeddings (EmbeddingClient): Embedding client used by the service.
            text_extractor (TextExtractor): Text extractor used by the service.
            chunker (TokenTextChunker): Text chunker used by the service.
        """
        self.documents = document_repository
        self.chunks = chunk_repository
        self.storage = storage
        self.embeddings = embeddings
        self.text_extractor = text_extractor
        self.chunker = chunker

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

            text = await self.text_extractor.extract(data, document.content_type)
            text_chunks = await self.chunker.chunk(text)

            embeddings = await self.embeddings.create_embedding(
                [chunk.content for chunk in text_chunks]
            )

            await self._persist_chunks(document, text_chunks, embeddings)

            document = await self._set_document_ready(document)

        except Exception as exc:
            logger.exception("Document processing failed: id={}", document_id)

            await self._set_document_failed(document, str(exc))

            raise

        logger.info("Document processing finished: id={}", document_id)

        return document

    async def _persist_chunks(
        self,
        document: Document,
        text_chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Build and persist document chunks from text and embeddings.

        Args:
            document (Document): Source document the chunks belong to.
            text_chunks (list[TextChunk]): Ordered text chunks to persist.
            embeddings (list[list[float]]): Embedding vectors aligned with
                ``text_chunks`` by index.

        Raises:
            ChunkEmbeddingCountMismatchError: If the number of text chunks and
                embeddings differ.
        """
        if len(text_chunks) != len(embeddings):
            raise ChunkEmbeddingCountMismatchError()

        chunks = []

        for text_chunk, embedding in zip(text_chunks, embeddings, strict=True):
            chunks.append(
                DocumentChunk(
                    user_id=document.user_id,
                    session_id=document.session_id,
                    document_id=document.id,
                    chunk_index=text_chunk.index,
                    content=text_chunk.content,
                    content_hash=text_chunk.content_hash,
                    token_count=text_chunk.token_count,
                    embedding=embedding,
                    embedding_model=settings.open_ai_embedding_model,
                )
            )

        await self.chunks.create_many(chunks)

    async def _set_document_ready(self, document: Document) -> Document:
        """Mark a document as successfully processed.

        Args:
            document (Document): Document to mark as ready.

        Returns:
            Document: Updated document in the ``READY`` status.
        """
        document.status = DocumentStatus.READY
        document.error_message = None

        return await self.documents.update(document)

    async def _set_document_failed(self, document: Document, error: str) -> Document:
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
