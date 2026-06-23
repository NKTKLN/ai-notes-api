"""Document schemas module.

This module defines Pydantic schemas used for document API requests and
responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import DocumentStatus


class DocumentRead(BaseModel):
    """Schema for returning document data.

    Attributes:
        id (UUID): Unique document identifier.
        chat_session_id (UUID): Unique chat session identifier.
        filename (str): Original document file name.
        content_type (str): MIME type of the document.
        file_size (int): Document size in bytes.
        checksum_sha256 (str): SHA-256 checksum of the document content.
        status (DocumentStatus): Current document processing status.
        error_message (str | None): Optional error message if document
            processing failed.
        created_at (datetime): Date and time when the document was created.
        updated_at (datetime): Date and time when the document was last updated.
        processed_at (datetime | None): Optional date and time when the document
            finished processing.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    chat_session_id: UUID = Field(validation_alias="session_id")

    filename: str
    content_type: str
    file_size: int
    checksum_sha256: str

    status: DocumentStatus
    error_message: str | None = None

    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None


class DocumentListResponse(BaseModel):
    """Schema for returning a paginated list of documents.

    Attributes:
        items (list[DocumentRead]): List of documents.
        limit (int): Maximum number of documents returned.
        offset (int): Number of documents skipped before returning results.
        total (int): Total number of documents in the current page.
    """

    items: list[DocumentRead]
    limit: int
    offset: int
    total: int


class DocumentUploadResponse(BaseModel):
    """Schema for returning the result of a document upload.

    Attributes:
        id (UUID): Unique document identifier.
        chat_session_id (UUID): Unique chat session identifier.
        filename (str): Original document file name.
        status (DocumentStatus): Current document processing status.
        created_at (datetime): Date and time when the document was created.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    chat_session_id: UUID = Field(validation_alias="session_id")
    filename: str
    status: DocumentStatus
    created_at: datetime


class DocumentProcessResponse(BaseModel):
    """Schema for returning the result of a document processing request.

    Attributes:
        document_id (UUID): Unique document identifier.
        status (DocumentStatus): Current document processing status.
        message (str): Human-readable description of the processing result.
    """

    document_id: UUID
    status: DocumentStatus
    message: str


class DocumentDeleteResponse(BaseModel):
    """Schema for returning the result of a document deletion.

    Attributes:
        document_id (UUID): Unique document identifier.
        status (DocumentStatus): Current document status.
        message (str): Human-readable description of the deletion result.
    """

    document_id: UUID
    status: DocumentStatus
    message: str


class DocumentDownloadUrlResponse(BaseModel):
    """Schema for returning a presigned document download URL.

    Attributes:
        url (str): Presigned URL used to download the document.
        expires_in_seconds (int): Number of seconds until the URL expires.
    """

    url: str
    expires_in_seconds: int
