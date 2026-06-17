"""Chat memory schemas module.

This module defines Pydantic schemas used for chat memory API requests and
responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMemoryResponseSchema(BaseModel):
    """Schema for returning chat memory data.

    Attributes:
        session_id (UUID): Unique identifier of the chat session associated with
            the memory.
        summary (str): Chat memory summary.
        facts (list[dict[str, Any]]): Structured facts extracted from the chat memory.
        is_summarizing (bool): Whether chat memory summarization is currently in
            progress.
        created_at (datetime): Date and time when the chat memory was created.
        updated_at (datetime): Date and time when the chat memory was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    summary: str
    facts: list[dict[str, Any]]
    is_summarizing: bool

    created_at: datetime
    updated_at: datetime


class ChatMemoryUpdateSchema(BaseModel):
    """Schema for updating chat memory.

    Attributes:
        summary (str | None): Optional chat memory summary.
        facts (list[dict[str, Any]] | None): Optional structured facts
            extracted from the chat memory.
        is_summarizing (bool | None): Optional flag indicating whether chat
            memory summarization is currently in progress.
    """

    summary: str | None = Field(
        default=None,
    )

    facts: list[dict[str, Any]] | None = Field(
        default=None,
    )

    is_summarizing: bool | None = Field(
        default=None,
    )
