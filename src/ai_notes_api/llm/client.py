"""OpenAI LLM client module.

This module provides an OpenAI-backed implementation of the LLM client
interface for generating responses, streaming responses, and creating
embeddings.
"""

from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from openai import AsyncOpenAI

from ai_notes_api.core import settings
from ai_notes_api.llm.models import LLMResponse, LLMStreamEvent, LLMToolCall


class LLMClient:
    """LLM client backed by the OpenAI API.

    Args:
        client (AsyncOpenAI): Shared asynchronous OpenAI client.
    """

    def __init__(self, client: AsyncOpenAI) -> None:
        """Initialize the LLM client.

        Args:
            client (AsyncOpenAI): Shared asynchronous OpenAI client.
        """
        self.client = client

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
            "model": settings.open_ai_model,
            "input": input_data,
            "max_output_tokens": max_output_tokens
            or settings.open_ai_max_output_tokens,
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

        logger.debug(
            "LLM response mapped: output_items={}, tool_calls={}",
            len(output_items),
            len(tool_calls),
        )

        return LLMResponse(
            text=getattr(response, "output_text", "") or "",
            tool_calls=tool_calls,
            output_items=output_items,
            raw=response,
        )

    async def create_response(  # noqa: PLR0913
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

        logger.debug(
            "Creating LLM response: model={}, tools={}, max_output_tokens={}",
            kwargs["model"],
            len(tools) if tools is not None else 0,
            kwargs["max_output_tokens"],
        )

        response = await self.client.responses.create(**kwargs)

        logger.info("LLM response created: model={}", kwargs["model"])

        return self._map_response(response)

    async def get_text_response(  # noqa: PLR0913
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
        response = await self.create_response(
            input_data=input_data,
            tools=tools,
            instructions=instructions,
            text_format=text_format,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        return response.text

    async def stream_response_events(
        self,
        input_data: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[LLMStreamEvent]:
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

        logger.debug(
            "Streaming LLM response: model={}, tools={}, max_output_tokens={}",
            kwargs["model"],
            len(tools) if tools is not None else 0,
            kwargs["max_output_tokens"],
        )

        response_id = None

        async with self.client.responses.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "response.created":
                    response_id = event.response.id

                if event.type == "response.output_text.delta":
                    yield LLMStreamEvent(
                        type="delta",
                        id=f"{response_id}:{event.sequence_number}",
                        delta=event.delta,
                    )

            final_response = await stream.get_final_response()

        logger.info("LLM stream completed: model={}", kwargs["model"])

        yield LLMStreamEvent(
            type="final",
            response=self._map_response(final_response),
        )
