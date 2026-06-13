"""OpenAI LLM client module.

This module provides an OpenAI-backed implementation of the LLM client
interface for generating responses, streaming responses, and creating
embeddings.
"""

from collections.abc import Generator
from typing import Any

from openai import OpenAI

from ai_notes_api.core import settings
from ai_notes_api.llm.base import BaseLLMClient
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent, LLMToolCall


class OpenAILLMClient(BaseLLMClient):
    """LLM client backed by the OpenAI API."""

    def __init__(self) -> None:
        """Initialize the OpenAI client from application settings."""
        self.client = OpenAI(
            api_key=settings.OPEN_AI_API_KEY,
            base_url=settings.OPEN_AI_API_URL,
        )

        self.model = settings.OPEN_AI_MODEL
        self.embedding_model = settings.OPEN_AI_EMBEDDING_MODEL
        self.max_output_tokens = settings.OPEN_AI_MAX_OUTPUT_TOKENS

    def _build_response_kwargs(  # noqa: PLR0913
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        instructions: str | None = None,
        text_format: dict[str, Any] | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Build keyword arguments for an OpenAI responses API call.

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
            dict[str, Any]: Keyword arguments to pass to the responses API.
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": input_data,
            "max_output_tokens": max_output_tokens
            or settings.OPEN_AI_MAX_OUTPUT_TOKENS,
        }

        if tools is not None:
            kwargs["tools"] = tools

        if instructions is not None:
            kwargs["instructions"] = instructions

        if text_format is not None:
            kwargs["text"] = {"format": text_format}

        if temperature is not None:
            kwargs["temperature"] = temperature

        return kwargs

    def _map_response(self, response: Any) -> LLMResponse:
        """Map a raw OpenAI response to an LLMResponse.

        Args:
            response (Any): Raw response object returned by the OpenAI API.

        Returns:
            LLMResponse: Normalized response with text, tool calls, and output
            items.
        """
        tool_calls: list[LLMToolCall] = []

        output_items = list(getattr(response, "output", []))

        for item in output_items:
            if getattr(item, "type", None) == "function_call":
                tool_calls.append(
                    LLMToolCall(
                        name=item.name,
                        arguments=item.arguments,
                        call_id=item.call_id,
                        raw=item,
                    )
                )

        return LLMResponse(
            text=getattr(response, "output_text", "") or "",
            tool_calls=tool_calls,
            output_items=output_items,
            raw=response,
        )

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
        kwargs = self._build_response_kwargs(
            input_data=input_data,
            tools=tools,
            instructions=instructions,
            text_format=text_format,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        response = self.client.responses.create(**kwargs)

        return self._map_response(response)

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
        response = self.create_response(
            input_data=input_data,
            tools=tools,
            instructions=instructions,
            text_format=text_format,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        return response.text

    def create_embedding(self, texts: list[str]) -> list[list[float]]:
        """Create embedding vectors for the given texts.

        Args:
            texts (list[str]): Texts to embed.

        Returns:
            list[list[float]]: Embedding vector for each input text, or an
            empty list if no texts are provided.
        """
        if not texts:
            return []

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
            encoding_format="float",
        )

        return [item.embedding for item in response.data]

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
        kwargs = self._build_response_kwargs(
            input_data=input_data,
            tools=tools,
            instructions=None,
            text_format=None,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        with self.client.responses.stream(**kwargs) as stream:
            for event in stream:
                if event.type == "response.output_text.delta":
                    yield LLMStreamEvent(
                        type="delta",
                        delta=event.delta,
                    )

            final_response = stream.get_final_response()

        yield LLMStreamEvent(
            type="final",
            response=self._map_response(final_response),
        )
