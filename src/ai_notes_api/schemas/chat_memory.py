"""Chat memory schemas module.

This module defines Pydantic schemas used for chat memory API requests and
responses.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatMemoryResponseSchema(BaseModel):
    """Schema for returning chat memory data.

    Attributes:
        session_id (UUID): Unique identifier of the chat session associated with
            the memory.
        summary (str): Chat memory summary.
        facts (list[dict[str, Any]]): Structured facts extracted from the chat memory.
        created_at (datetime): Date and time when the chat memory was created.
        updated_at (datetime): Date and time when the chat memory was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    summary: str
    facts: list[dict[str, Any]]

    created_at: datetime
    updated_at: datetime


class ChatMemoryUpdateSchema(BaseModel):
    """Schema for updating chat memory.

    Attributes:
        summary (str): Updated chat memory summary.
        facts (list[dict[str, Any]]): Updated structured facts extracted from
            the chat memory.
    """

    summary: str
    facts: list[dict[str, Any]]
