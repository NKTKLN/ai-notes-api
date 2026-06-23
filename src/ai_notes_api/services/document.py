"""Document service module.

This module provides business logic for working with documents.
"""

import hashlib
from uuid import UUID, uuid4

from fastapi import UploadFile

from ai_notes_api.db.models import (
    Document,
    DocumentProcessingJob,
    DocumentProcessingJobStatus,
    DocumentStatus,
)
from ai_notes_api.exceptions import DocumentNotFoundError
from ai_notes_api.repositories import (
    DocumentProcessingJobRepository,
    DocumentRepository,
)
from ai_notes_api.services.chat_session import ChatSessionService
from ai_notes_api.storage import DocumentStorage
from ai_notes_api.workers.tasks.processing import run_document_processing_job


class DocumentService:
    """Service for document-related business operations.

    Args:
        document_repository (DocumentRepository): Repository used to perform
            document database operations.
        processing_repository (DocumentProcessingJobRepository): Repository used
            to create document processing jobs.
        session_service (ChatSessionService): Chat session service used to
            validate chat session access.
        storage (DocumentStorage): Object storage helper used to manage document files.
    """

    DEFAULT_FILENAME = "document"
    DEFAULT_CONTENT_TYPE = "application/octet-stream"

    def __init__(
        self,
        document_repository: DocumentRepository,
        processing_repository: DocumentProcessingJobRepository,
        session_service: ChatSessionService,
        storage: DocumentStorage,
    ) -> None:
        """Initialize the document service.

        Args:
            document_repository (DocumentRepository): Document repository used by
                the service.
            processing_repository (DocumentProcessingJobRepository): Document
                processing job repository used by the service.
            session_service (ChatSessionService): Chat session service used by the
                service.
            storage (DocumentStorage): Object storage helper used by the service.
        """
        self.documents = document_repository
        self.sessions = session_service
        self.processing = processing_repository
        self.storage = storage

    async def create_document(
        self,
        user_id: UUID,
        chat_session_id: UUID,
        file: UploadFile,
    ) -> Document:
        """Upload a file and create a document for a chat session.

        Reads the uploaded file, stores it in object storage, persists a
        document record in the ``UPLOADED`` status, and enqueues a processing
        job for it.

        Args:
            user_id (UUID): Unique identifier of the user uploading the document.
            chat_session_id (UUID): Unique chat session identifier.
            file (UploadFile): Uploaded file to store as a document.

        Returns:
            Document: Created document.

        Raises:
            ChatSessionNotFoundError: If no accessible chat session exists.
        """
        await self.sessions.ensure_session_owner(user_id, chat_session_id)

        data = await file.read()

        document_id = uuid4()
        filename = file.filename or self.DEFAULT_FILENAME
        content_type = file.content_type or self.DEFAULT_CONTENT_TYPE
        checksum = hashlib.sha256(data).hexdigest()

        object_name = await self.storage.upload_file(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
            data=data,
            content_type=content_type,
        )

        document = Document(
            id=document_id,
            user_id=user_id,
            session_id=chat_session_id,
            filename=filename,
            content_type=content_type,
            file_size=len(data),
            checksum_sha256=checksum,
            storage_bucket=self.storage.bucket,
            storage_object_name=object_name,
            status=DocumentStatus.UPLOADED,
        )

        document = await self.documents.create(document)

        processing_job = await self.processing.create(
            DocumentProcessingJob(
                document_id=document_id,
                status=DocumentProcessingJobStatus.QUEUED,
            )
        )

        run_document_processing_job.delay(str(processing_job.id))

        return document

    async def list_chat_documents(
        self,
        user_id: UUID,
        chat_session_id: UUID,
    ) -> list[Document]:
        """Return a user's documents for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the documents.
            chat_session_id (UUID): Unique chat session identifier.

        Returns:
            list[Document]: List of the user's documents in the chat session.
        """
        return await self.documents.get_list_for_session(user_id, chat_session_id)

    async def get_chat_document(
        self,
        user_id: UUID,
        chat_session_id: UUID,
        document_id: UUID,
    ) -> Document:
        """Return a user's document from a chat session by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the document.
            chat_session_id (UUID): Unique chat session identifier.
            document_id (UUID): Unique document identifier.

        Returns:
            Document: Matching document.

        Raises:
            DocumentNotFoundError: If no accessible document exists in the chat session.
        """
        document = await self.documents.get_by_id_for_user(user_id, document_id)

        if document is None or document.session_id != chat_session_id:
            raise DocumentNotFoundError()

        return document

    async def delete_document(
        self,
        user_id: UUID,
        chat_session_id: UUID,
        document_id: UUID,
    ) -> None:
        """Delete a user's document from a chat session.

        Soft-deletes the document and its chunks, then removes the stored file
        from object storage.

        Args:
            user_id (UUID): Unique identifier of the user who owns the document.
            chat_session_id (UUID): Unique chat session identifier.
            document_id (UUID): Unique document identifier to delete.

        Raises:
            DocumentNotFoundError: If no accessible document exists in the chat session.
        """
        document = await self.get_chat_document(
            user_id,
            chat_session_id,
            document_id,
        )

        await self.documents.soft_delete(document)
        await self.storage.delete_file(document.storage_object_name)
