"""Chat session database model module.

This module defines the SQLAlchemy ORM model for chat sessions.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_memory import ChatMemory
    from ai_notes_api.db.models.document import Document
    from ai_notes_api.db.models.document_chunk import DocumentChunk
    from ai_notes_api.db.models.generation_job import GenerationJob
    from ai_notes_api.db.models.message import Message
    from ai_notes_api.db.models.user import User


class ChatSessionGenerationStatus(StrEnum):
    """Chat session LLM generation status.

    Attributes:
        IDLE (str): Chat session has no active generation.
        RUNNING (str): Chat session has an active generation.
    """

    IDLE = "idle"
    RUNNING = "running"


class ChatSession(Base, TimestampMixin, SoftDeleteMixin):
    """SQLAlchemy ORM model representing a chat session.

    Attributes:
        id (Mapped[UUID]): Unique chat session identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the chat session.
        user (Mapped[User]): User who owns the chat session.
        title (Mapped[str]): Chat session title.
        generation_status (Mapped[ChatSessionGenerationStatus]): Current LLM
            generation status for the chat session.
        generation_id (Mapped[UUID | None]): Optional active generation identifier.
        generation_started_at (Mapped[datetime | None]): Date and time when the
            active generation started.
        messages (Mapped[list[Message]]): Messages that belong to the chat session.
        generation_jobs (Mapped[list[GenerationJob]]): Generation jobs that
            belong to the chat session.
        memory (Mapped[ChatMemory]): Memory associated with the chat session.
        documents (Mapped[list[Document]]): Documents that belong to the chat session.
        document_chunks (Mapped[list[DocumentChunk]]): Document chunks that
            belong to the chat session.
    """

    __tablename__ = "chat_sessions"

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
        back_populates="chat_sessions",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    generation_status: Mapped[ChatSessionGenerationStatus] = mapped_column(
        SqlEnum(
            ChatSessionGenerationStatus,
            name="chat_session_generation_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=ChatSessionGenerationStatus.IDLE,
        server_default=ChatSessionGenerationStatus.IDLE.value,
        index=True,
    )

    generation_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
    )

    generation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )

    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )

    memory: Mapped["ChatMemory"] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )

    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )
