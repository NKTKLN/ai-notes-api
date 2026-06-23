"""Document chunk database model module.

This module defines the SQLAlchemy ORM model for document chunks and their
vector embeddings used for semantic search.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.document import Document
    from ai_notes_api.db.models.rag_query_source import RagQuerySource
    from ai_notes_api.db.models.user import User


class DocumentChunk(Base, TimestampMixin, SoftDeleteMixin):
    """SQLAlchemy ORM model representing a document chunk.

    Attributes:
        id (Mapped[UUID]): Unique document chunk identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the document
            chunk.
        user (Mapped[User]): User who owns the document chunk.
        session_id (Mapped[UUID]): Identifier of the chat session that owns the
            document chunk.
        chat_session (Mapped[ChatSession]): Chat session that owns the document
            chunk.
        document_id (Mapped[UUID]): Identifier of the document the chunk belongs
            to.
        document (Mapped[Document]): Document the chunk belongs to.
        chunk_index (Mapped[int]): Position of the chunk within the document.
        content (Mapped[str]): Text content of the chunk.
        content_hash (Mapped[str]): Hash of the chunk content.
        embedding (Mapped[list[float]]): Vector embedding of the chunk content.
        embedding_model (Mapped[str]): Name of the model used to produce the
            embedding.
        token_count (Mapped[int | None]): Optional number of tokens in the
            chunk.
        rag_query_sources (Mapped[list[RagQuerySource]]): RAG query sources that
            reference the chunk.
    """

    __tablename__ = "document_chunks"

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
        back_populates="document_chunks",
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
        back_populates="document_chunks",
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
        back_populates="document_chunks",
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    token_count: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    rag_query_sources: Mapped[list["RagQuerySource"]] = relationship(
        back_populates="chunk",
        cascade="all, delete-orphan",
    )
