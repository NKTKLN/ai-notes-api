"""RAG schemas module.

This module defines Pydantic schemas used for RAG query API requests and
responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import RagQueryStatus


class RagQueryRequest(BaseModel):
    """Schema for creating a RAG query.

    Attributes:
        question (str): User question.
        top_k (int): Number of document chunks to retrieve for the query.
    """

    question: str = Field(min_length=1, max_length=10_000)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSourceRead(BaseModel):
    """Schema for returning a RAG query source.

    Attributes:
        document_id (UUID): Unique document identifier.
        chunk_id (UUID): Unique document chunk identifier.
        rank (int): Rank of the chunk among the retrieved sources.
        score (float): Relevance score of the chunk for the query.
        preview (str): Preview of the chunk content.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    document_id: UUID
    chunk_id: UUID
    rank: int
    score: float
    preview: str = Field(validation_alias="content_preview")


class RagQueryResponse(BaseModel):
    """Schema for returning RAG query data.

    Attributes:
        id (UUID): Unique RAG query identifier.
        chat_session_id (UUID): Unique chat session identifier.
        question (str): User question.
        answer (str | None): Optional generated answer.
        provider (str | None): Optional AI provider name.
        model (str | None): Optional AI model name.
        top_k (int): Number of document chunks retrieved for the query.
        status (RagQueryStatus): Current RAG query status.
        sources (list[RagSourceRead]): Sources retrieved for the RAG query.
        created_at (datetime): Date and time when the RAG query was created.
        finished_at (datetime | None): Date and time when the RAG query finished.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    chat_session_id: UUID = Field(validation_alias="session_id")

    question: str
    answer: str | None = None

    provider: str | None = None
    model: str | None = None

    top_k: int
    status: RagQueryStatus

    sources: list[RagSourceRead] = Field(default_factory=list)

    created_at: datetime
    finished_at: datetime | None = None
