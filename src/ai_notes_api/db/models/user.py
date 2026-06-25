"""User database model module.

This module defines the SQLAlchemy ORM model for application users.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.document import Document
    from ai_notes_api.db.models.document_chunk import DocumentChunk
    from ai_notes_api.db.models.generation_job import GenerationJob
    from ai_notes_api.db.models.note import Note
    from ai_notes_api.db.models.rag_query import RagQuery


class User(Base, TimestampMixin):
    """SQLAlchemy ORM model representing an application user.

    Attributes:
        id (Mapped[UUID]): Unique user identifier.
        email (Mapped[str]): Unique user email address.
        username (Mapped[str | None]): Optional username.
        hashed_password (Mapped[str]): Hashed user password.
        is_active (Mapped[bool]): Whether the user account is active.
        is_superuser (Mapped[bool]): Whether the user has superuser privileges.
        notes (Mapped[list[Note]]): Notes owned by the user.
        chat_sessions (Mapped[list[ChatSession]]): Chat sessions owned by the user.
        generation_jobs (Mapped[list[GenerationJob]]): Generation jobs owned by
            the user.
        documents (Mapped[list[Document]]): Documents owned by the user.
        document_chunks (Mapped[list[DocumentChunk]]): Document chunks owned by
            the user.
        rag_queries (Mapped[list[RagQuery]]): RAG queries owned by the user.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
    )

    is_superuser: Mapped[bool] = mapped_column(
        default=False,
    )

    notes: Mapped[list["Note"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    rag_queries: Mapped[list["RagQuery"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
