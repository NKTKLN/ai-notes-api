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
        is_summarizing (bool): Whether chat memory summarization is currently in
            progress.
        last_summarized_message (UUID | None): Unique identifier of the last
            message included in the chat memory summary, if any.
        created_at (datetime): Date and time when the chat memory was created.
        updated_at (datetime): Date and time when the chat memory was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    summary: str
    facts: list[dict[str, Any]]
    is_summarizing: bool
    last_summarized_message: UUID | None

    created_at: datetime
    updated_at: datetime
