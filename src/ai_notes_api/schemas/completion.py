"""Chat completion schemas module.

This module defines Pydantic schemas used for chat completion API responses.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatCompletionResponseSchema(BaseModel):
    """Schema for returning a chat completion response.

    Attributes:
        message_id (UUID | None): Optional identifier of the saved assistant message.
        answer (str): Generated assistant answer.
        provider (str): AI provider name.
        model_name (str): AI model name.
        prompt_tokens (int | None): Optional number of prompt tokens.
        completion_tokens (int | None): Optional number of completion tokens.
        total_tokens (int | None): Optional total number of tokens.
    """

    message_id: UUID | None = None

    answer: str = Field(min_length=1)

    provider: str
    model_name: str

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
