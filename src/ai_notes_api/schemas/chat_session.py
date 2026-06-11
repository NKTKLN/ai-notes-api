"""Chat session schemas module.

This module defines Pydantic schemas used for chat session API requests and
responses.
"""

from datetime import datetime

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreateSchema(BaseModel):
    """Schema for creating a chat session.

    Attributes:
        title (str): Chat session title.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )


class ChatSessionUpdateSchema(BaseModel):
    """Schema for updating a chat session.

    Attributes:
        title (str): Updated chat session title.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )


class ChatSessionResponseSchema(BaseModel):
    """Schema for returning chat session data.

    Attributes:
        id (int): Unique chat session identifier.
        title (str): Chat session title.
        created_at (datetime): Date and time when the chat session was created.
        updated_at (datetime): Date and time when the chat session was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponseSchema(BaseModel):
    """Schema for returning a paginated list of chat sessions.

    Attributes:
        items (list[ChatSessionResponseSchema]): List of chat sessions.
        limit (int): Maximum number of chat sessions returned.
        offset (int): Number of chat sessions skipped before returning results.
        total (int): Total number of chat sessions in the current page.
    """

    items: list[ChatSessionResponseSchema]
    limit: int
    offset: int
    total: int


class ChatSessionListQuerySchema(BaseModel):
    """Schema for chat session list query parameters.

    Attributes:
        limit (int): Maximum number of chat sessions to return.
        offset (int): Number of chat sessions to skip before returning results.
        search (str | None): Optional text used to search chat sessions by title.
    """

    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)
    search: str | None = None
