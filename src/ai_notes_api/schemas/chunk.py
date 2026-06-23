"""Document chunk schemas module.

This module defines Pydantic schemas used for document chunk API responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkRead(BaseModel):
    """Schema for returning document chunk data.

    Attributes:
        id (UUID): Unique document chunk identifier.
        document_id (UUID): Unique document identifier.
        chat_session_id (UUID): Unique chat session identifier.
        chunk_index (int): Position of the chunk within the document.
        content (str): Text content of the chunk.
        embedding_model (str): Name of the model used to produce the embedding.
        token_count (int | None): Optional number of tokens in the chunk.
        created_at (datetime): Date and time when the chunk was created.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    document_id: UUID
    chat_session_id: UUID = Field(validation_alias="session_id")

    chunk_index: int
    content: str
    embedding_model: str
    token_count: int | None = None

    created_at: datetime
