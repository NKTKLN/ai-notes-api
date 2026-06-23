"""Document service module.

This module provides business logic for working with documents.
"""

import hashlib
from uuid import UUID, uuid4

from fastapi import UploadFile

from ai_notes_api.db.models import Document, DocumentStatus
from ai_notes_api.exceptions import DocumentNotFoundError
from ai_notes_api.repositories import DocumentRepository
from ai_notes_api.storage import DocumentStorage

DEFAULT_FILENAME = "document"
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class DocumentService:
    """Service for document-related business operations.

    Args:
        repository (DocumentRepository): Repository used to perform document
            database operations.
        storage (DocumentStorage): Object storage helper used to manage document
            files.
    """

    def __init__(
        self,
        repository: DocumentRepository,
        storage: DocumentStorage,
    ) -> None:
        """Initialize the document service.

        Args:
            repository (DocumentRepository): Document repository used by the service.
            storage (DocumentStorage): Object storage helper used by the service.
        """
        self.documents = repository
        self.storage = storage

    async def create_document(
        self,
        user_id: UUID,
        chat_session_id: UUID,
        file: UploadFile,
    ) -> Document:
        """Upload a file and create a document for a chat session.

        Reads the uploaded file, stores it in object storage, and persists a
        document record in the ``UPLOADED`` status.

        Args:
            user_id (UUID): Unique identifier of the user uploading the document.
            chat_session_id (UUID): Unique chat session identifier.
            file (UploadFile): Uploaded file to store as a document.

        Returns:
            Document: Created document.
        """
        data = await file.read()

        document_id = uuid4()
        filename = file.filename or DEFAULT_FILENAME
        content_type = file.content_type or DEFAULT_CONTENT_TYPE
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

        return await self.documents.create(document)

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
