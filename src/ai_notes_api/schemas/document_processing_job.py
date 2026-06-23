"""Document processing job schemas module.

This module defines Pydantic schemas used for document processing job API
responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ai_notes_api.db.models import DocumentProcessingJobStatus


class DocumentProcessingJobRead(BaseModel):
    """Schema for returning document processing job data.

    Attributes:
        id (UUID): Unique processing job identifier.
        document_id (UUID): Unique document identifier.
        status (DocumentProcessingJobStatus): Current processing job status.
        created_at (datetime): Date and time when the processing job was created.
        started_at (datetime | None): Date and time when processing started.
        finished_at (datetime | None): Date and time when processing finished.
        error (str | None): Optional error message if processing failed.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    status: DocumentProcessingJobStatus

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
