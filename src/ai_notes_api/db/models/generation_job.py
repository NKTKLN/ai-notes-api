"""Generation job database model module.

This module defines the SQLAlchemy ORM model for LLM generation jobs and the
enum used to track generation job status.
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
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.message import Message
    from ai_notes_api.db.models.user import User


class GenerationJobStatus(StrEnum):
    """Status of an LLM generation job.

    Attributes:
        QUEUED (str): Generation job is waiting to be processed.
        RUNNING (str): Generation job is currently being processed.
        COMPLETED (str): Generation job completed successfully.
        FAILED (str): Generation job failed.
        CANCELLED (str): Generation job was cancelled.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationJob(Base, TimestampMixin):
    """SQLAlchemy ORM model representing an LLM generation job.

    Attributes:
        id (Mapped[UUID]): Unique generation job identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the generation job.
        user (Mapped[User]): User who owns the generation job.
        session_id (Mapped[UUID]): Identifier of the chat session associated
            with the generation job.
        chat_session (Mapped[ChatSession]): Chat session associated with the
            generation job.
        status (Mapped[GenerationJobStatus]): Current generation job status.
        input_message (Mapped[str]): User input message used for generation.
        output_message_id (Mapped[UUID | None]): Optional identifier of the
            generated assistant message.
        output_message (Mapped[Message | None]): Generated assistant message.
        error (Mapped[str | None]): Optional error message if generation failed.
        started_at (Mapped[datetime | None]): Date and time when generation started.
        finished_at (Mapped[datetime | None]): Date and time when generation finished.
    """

    __tablename__ = "generation_jobs"

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
        back_populates="generation_jobs",
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
        back_populates="generation_jobs",
    )

    status: Mapped[GenerationJobStatus] = mapped_column(
        SqlEnum(
            GenerationJobStatus,
            name="generation_job_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=GenerationJobStatus.QUEUED,
        nullable=False,
    )

    input_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    output_message_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    output_message: Mapped["Message | None"] = relationship(
        back_populates="generation_job",
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
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
