"""Document processing job database model module.

This module defines the SQLAlchemy ORM model for document processing jobs and
the enum used to track processing job status.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.document import Document


class DocumentProcessingJobStatus(StrEnum):
    """Status of a document processing job.

    Attributes:
        QUEUED (str): Processing job is waiting to be processed.
        RUNNING (str): Processing job is currently being processed.
        COMPLETED (str): Processing job completed successfully.
        FAILED (str): Processing job failed.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentProcessingJob(Base, TimestampMixin):
    """SQLAlchemy ORM model representing a document processing job.

    Attributes:
        id (Mapped[UUID]): Unique processing job identifier.
        document_id (Mapped[UUID]): Identifier of the document the processing job
            belongs to.
        document (Mapped[Document]): Document the processing job belongs to.
        status (Mapped[DocumentProcessingJobStatus]): Current processing job status.
        started_at (Mapped[datetime | None]): Date and time when processing started.
        finished_at (Mapped[datetime | None]): Date and time when processing finished.
        error (Mapped[str | None]): Optional error message if processing failed.
    """

    __tablename__ = "document_processing_jobs"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    document: Mapped["Document"] = relationship(
        back_populates="processing_jobs",
    )

    status: Mapped[DocumentProcessingJobStatus] = mapped_column(
        SqlEnum(
            DocumentProcessingJobStatus,
            name="document_processing_job_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=DocumentProcessingJobStatus.QUEUED,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
    )
