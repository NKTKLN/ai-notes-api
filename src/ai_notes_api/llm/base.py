"""Base LLM client module.

This module defines the abstract interface that concrete LLM clients must
implement to generate responses, stream responses, and create embeddings.
"""

from abc import ABC, abstractmethod
from collections.abc import Generator
from typing import Any

from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent


class BaseLLMClient(ABC):
    """Abstract base class for large language model clients."""

    @abstractmethod
    def create_response(  # noqa: PLR0913
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        text_format: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Generate a full response from the model.

        Args:
            input_data (str | list[dict[str, Any]]): Prompt text or a list of
                structured input messages.
            tools (list[dict[str, Any]] | None): Optional tool definitions the
                model may call.
            instructions (str | None): Optional system-level instructions.
            text_format (dict[str, Any] | None): Optional structured output
                format specification.
            max_output_tokens (int | None): Optional maximum number of tokens
                to generate.
            temperature (float | None): Optional sampling temperature.

        Returns:
            LLMResponse: Generated response including text and tool calls.
        """
        pass

    @abstractmethod
    def get_text_response(  # noqa: PLR0913
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        text_format: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response and return only its text.

        Args:
            input_data (str | list[dict[str, Any]]): Prompt text or a list of
                structured input messages.
            tools (list[dict[str, Any]] | None): Optional tool definitions the
                model may call.
            instructions (str | None): Optional system-level instructions.
            text_format (dict[str, Any] | None): Optional structured output
                format specification.
            max_output_tokens (int | None): Optional maximum number of tokens
                to generate.
            temperature (float | None): Optional sampling temperature.

        Returns:
            str: Generated response text.
        """
        pass

    @abstractmethod
    def stream_response_events(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Generator[LLMStreamEvent]:
        """Stream response events from the model as they are produced.

        Args:
            input_data (str | list[dict[str, Any]]): Prompt text or a list of
                structured input messages.
            tools (list[dict[str, Any]] | None): Optional tool definitions the
                model may call.
            max_output_tokens (int | None): Optional maximum number of tokens
                to generate.
            temperature (float | None): Optional sampling temperature.

        Yields:
            LLMStreamEvent: Incremental delta events followed by a final event
            containing the complete response.
        """
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Create embedding vectors for the given texts.

        Args:
            texts (list[str]): Texts to embed.

        Returns:
            list[list[float]]: Embedding vector for each input text.
        """
        pass
