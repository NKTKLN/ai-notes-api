"""Message schemas module.

This module defines Pydantic schemas used for message API requests and
responses.
"""

from datetime import datetime
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import MessageRole


class UserMessageCreateSchema(BaseModel):
    """Schema for creating a user message.

    Attributes:
        session_id (UUID): Unique chat session identifier.
        content (str): User message content.
    """

    session_id: UUID
    content: str = Field(min_length=1, max_length=10_000)


class AssistantMessageCreateSchema(BaseModel):
    """Schema for creating an assistant message.

    Attributes:
        session_id (UUID): Unique chat session identifier.
        content (str): Assistant message content.
        provider (str | None): Optional AI provider name.
        model_name (str | None): Optional AI model name.
        prompt_tokens (int | None): Optional number of prompt tokens.
        completion_tokens (int | None): Optional number of completion tokens.
        total_tokens (int | None): Optional total number of tokens.
    """

    session_id: UUID
    content: str = Field(min_length=1)
    provider: str | None = None
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class MessageResponseSchema(BaseModel):
    """Schema for returning message data.

    Attributes:
        id (UUID): Unique message identifier.
        session_id (UUID): Unique chat session identifier.
        role (MessageRole): Message role.
        content (str): Message content.
        provider (str | None): Optional AI provider name.
        model_name (str | None): Optional AI model name.
        prompt_tokens (int | None): Optional number of prompt tokens.
        completion_tokens (int | None): Optional number of completion tokens.
        total_tokens (int | None): Optional total number of tokens.
        created_at (datetime): Date and time when the message was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str

    provider: str | None = None
    model_name: str | None = None

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    created_at: datetime


class MessageListResponseSchema(BaseModel):
    """Schema for returning a paginated list of messages.

    Attributes:
        items (list[MessageResponseSchema]): List of messages.
        limit (int): Maximum number of messages returned.
        offset (int): Number of messages skipped before returning results.
        total (int): Total number of messages in the current page.
    """

    items: list[MessageResponseSchema]
    limit: int
    offset: int
    total: int


class MessageListQuerySchema(BaseModel):
    """Schema for message list query parameters.

    Attributes:
        limit (int): Maximum number of messages to return.
        offset (int): Number of messages to skip before returning results.
        search (str | None): Optional text used to search message content.
        role (MessageRole | None): Optional message role used to filter results.
        model_name (str | None): Optional AI model name used to filter results.
        provider (str | None): Optional AI provider name used to filter results.
    """

    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)
    search: str | None = None
    role: MessageRole | None = None
    model_name: str | None = None
    provider: str | None = None
