"""RAG query source database model module.

This module defines the SQLAlchemy ORM model for RAG query sources, which link a
RAG query to the document chunks retrieved for it.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.document import Document
    from ai_notes_api.db.models.document_chunk import DocumentChunk
    from ai_notes_api.db.models.rag_query import RagQuery


class RagQuerySource(Base, TimestampMixin):
    """SQLAlchemy ORM model representing a RAG query source.

    Attributes:
        id (Mapped[UUID]): Unique RAG query source identifier.
        rag_query_id (Mapped[UUID]): Identifier of the RAG query the source
            belongs to.
        rag_query (Mapped[RagQuery]): RAG query the source belongs to.
        document_id (Mapped[UUID]): Identifier of the source document.
        document (Mapped[Document]): Source document.
        chunk_id (Mapped[UUID]): Identifier of the source document chunk.
        chunk (Mapped[DocumentChunk]): Source document chunk.
        score (Mapped[float]): Relevance score of the chunk for the query.
        rank (Mapped[int]): Rank of the chunk among the retrieved sources.
        content_preview (Mapped[str]): Preview of the chunk content.
    """

    __tablename__ = "rag_query_sources"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    rag_query_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "rag_queries.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    rag_query: Mapped["RagQuery"] = relationship(
        back_populates="sources",
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
        back_populates="rag_query_sources",
    )

    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "document_chunks.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    chunk: Mapped["DocumentChunk"] = relationship(
        back_populates="rag_query_sources",
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rank: Mapped[int] = mapped_column(
        nullable=False,
    )

    content_preview: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
