"""Document schemas module.

This module defines Pydantic schemas used for document API requests and
responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import DocumentStatus


class DocumentResponseSchema(BaseModel):
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


class DocumentListResponse(BaseModel):
    """Schema for returning a paginated list of documents.

    Attributes:
        items (list[DocumentRead]): List of documents.
        total (int): Total number of documents in the current page.
    """

    items: list[DocumentResponseSchema]
    total: int


class DocumentDownloadUrlResponse(BaseModel):
    """Schema for returning a presigned document download URL.

    Attributes:
        url (str): Presigned URL used to download the document.
        expires_in_seconds (int): Number of seconds until the URL expires.
    """

    url: str
    expires_in_seconds: int
