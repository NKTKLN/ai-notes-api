"""Document database model module.

This module defines the SQLAlchemy ORM model for chat documents and the enum
used to track document processing status.
"""

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.document_chunk import DocumentChunk
    from ai_notes_api.db.models.document_processing_job import DocumentProcessingJob
    from ai_notes_api.db.models.rag_query_source import RagQuerySource
    from ai_notes_api.db.models.user import User


class DocumentStatus(StrEnum):
    """Processing status of a chat document.

    Attributes:
        UPLOADED (str): Document has been uploaded but not yet processed.
        PROCESSING (str): Document is currently being processed.
        READY (str): Document was processed successfully and is ready for use.
        FAILED (str): Document processing failed.
        DELETED (str): Document was deleted.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """SQLAlchemy ORM model representing a chat document.

    Attributes:
        id (Mapped[UUID]): Unique document identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the document.
        user (Mapped[User]): User who owns the document.
        session_id (Mapped[UUID]): Identifier of the chat session that owns the
            document.
        chat_session (Mapped[ChatSession]): Chat session that owns the document.
        filename (Mapped[str]): Original document file name.
        content_type (Mapped[str]): MIME type of the document.
        file_size (Mapped[int]): Document size in bytes.
        checksum_sha256 (Mapped[str]): SHA-256 checksum of the document content.
        storage_bucket (Mapped[str]): Storage bucket where the document is stored.
        storage_object_name (Mapped[str]): Object name of the document within
            the storage bucket.
        status (Mapped[DocumentStatus]): Current document processing status.
        error_message (Mapped[str | None]): Optional error message if document
            processing failed.
        document_chunks (Mapped[list[DocumentChunk]]): Chunks that belong to the
            document.
        rag_query_sources (Mapped[list[RagQuerySource]]): RAG query sources that
            reference the document.
        processing_jobs (Mapped[list[DocumentProcessingJob]]): Processing jobs
            that belong to the document.
    """

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="documents",
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="documents",
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content_type: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        nullable=False,
    )

    checksum_sha256: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_bucket: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    storage_object_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[DocumentStatus] = mapped_column(
        SqlEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    rag_query_sources: Mapped[list["RagQuerySource"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    processing_jobs: Mapped[list["DocumentProcessingJob"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )
