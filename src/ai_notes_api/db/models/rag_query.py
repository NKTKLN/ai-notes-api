"""RAG query database model module.

This module defines the SQLAlchemy ORM model for RAG queries and the enum used
to track RAG query status.
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.user import User


class RagQueryStatus(StrEnum):
    """Status of a RAG query.

    Attributes:
        QUEUED (str): RAG query is waiting to be processed.
        RUNNING (str): RAG query is currently being processed.
        COMPLETED (str): RAG query completed successfully.
        FAILED (str): RAG query failed.
    """

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RagQuery(Base, TimestampMixin):
    """SQLAlchemy ORM model representing a RAG query.

    Attributes:
        id (Mapped[UUID]): Unique RAG query identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the RAG query.
        user (Mapped[User]): User who owns the RAG query.
        session_id (Mapped[UUID]): Identifier of the chat session that owns the
            RAG query.
        chat_session (Mapped[ChatSession]): Chat session that owns the RAG query.
        question (Mapped[str]): User question.
        answer (Mapped[str | None]): Optional generated answer.
        provider (Mapped[str | None]): Optional AI provider name.
        model (Mapped[str | None]): Optional AI model name.
        prompt_tokens (Mapped[int | None]): Optional number of prompt tokens.
        completion_tokens (Mapped[int | None]): Optional number of completion tokens.
        total_tokens (Mapped[int | None]): Optional total number of tokens.
        top_k (Mapped[int]): Number of document chunks retrieved for the query.
        status (Mapped[RagQueryStatus]): Current RAG query status.
        finished_at (Mapped[datetime | None]): Date and time when the RAG query
            finished.
        error_message (Mapped[str | None]): Optional error message if the RAG
            query failed.
    """

    __tablename__ = "rag_queries"

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
        back_populates="rag_queries",
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
        back_populates="rag_queries",
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    answer: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
    )

    provider: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    prompt_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    completion_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    top_k: Mapped[int] = mapped_column(
        nullable=False,
    )

    status: Mapped[RagQueryStatus] = mapped_column(
        SqlEnum(
            RagQueryStatus,
            name="rag_query_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=RagQueryStatus.QUEUED,
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
    )
