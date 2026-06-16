"""Tests for LLM client."""

from collections.abc import AsyncIterator
from types import SimpleNamespace, TracebackType
from unittest.mock import AsyncMock, Mock

import pytest

from ai_notes_api.llm.client import LLMClient


@pytest.fixture
def fake_openai_client() -> Mock:
    """Return a mocked OpenAI async client.

    Returns:
        Mock: Mocked OpenAI async client.
    """
    fake_client = Mock()

    fake_client.responses = Mock()
    fake_client.responses.create = AsyncMock()

    return fake_client


class FakeStream:
    """Fake OpenAI response stream used in streaming tests.

    Attributes:
        _events (Iterator[SimpleNamespace]): Iterator over fake stream events.
    """

    async def __aenter__(self) -> "FakeStream":
        """Enter the async context manager.

        Returns:
            FakeStream: Current fake stream instance.
        """
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager.

        Args:
            exc_type (type[BaseException] | None): Exception type, if raised.
            exc (BaseException | None): Exception instance, if raised.
            tb (TracebackType | None): Exception traceback, if raised.
        """

    def __aiter__(self) -> AsyncIterator[SimpleNamespace]:
        """Return the async iterator.

        Returns:
            AsyncIterator[SimpleNamespace]: Async iterator over fake events.
        """
        self._events = iter(
            [
                SimpleNamespace(
                    type="response.created",
                    response=SimpleNamespace(id="resp_123"),
                ),
                SimpleNamespace(
                    type="response.output_text.delta",
                    delta="Hel",
                    sequence_number=1,
                ),
                SimpleNamespace(
                    type="response.output_text.delta",
                    delta="lo",
                    sequence_number=2,
                ),
                SimpleNamespace(
                    type="response.completed",
                ),
            ]
        )
        return self

    async def __anext__(self) -> SimpleNamespace:
        """Return the next fake stream event.

        Returns:
            SimpleNamespace: Next fake stream event.

        Raises:
            StopAsyncIteration: If there are no more fake events.
        """
        try:
            return next(self._events)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def get_final_response(self) -> SimpleNamespace:
        """Return the final fake response.

        Returns:
            SimpleNamespace: Final fake response object.
        """
        return SimpleNamespace(output_text="Hello", output=[])


def test_build_response_kwargs_minimal() -> None:
    """Test response kwargs building with minimal input."""
    client = LLMClient(Mock())

    kwargs = client._build_response_kwargs(input_data="hello")

    assert kwargs["input"] == "hello"
    assert "model" in kwargs
    assert "max_output_tokens" in kwargs
    assert "tools" not in kwargs
    assert "instructions" not in kwargs
    assert "text" not in kwargs
    assert "temperature" not in kwargs


def test_build_response_kwargs_with_optional_params() -> None:
    """Test response kwargs building with optional parameters."""
    client = LLMClient(Mock())

    tools = [{"type": "function", "name": "search"}]
    text_format = {"type": "json_schema"}

    kwargs = client._build_response_kwargs(
        input_data="hello",
        tools=tools,
        instructions="Be concise",
        text_format=text_format,
        max_output_tokens=123,
        temperature=0.2,
    )

    assert kwargs["input"] == "hello"
    assert kwargs["tools"] == tools
    assert kwargs["instructions"] == "Be concise"
    assert kwargs["text"] == {"format": text_format}
    assert kwargs["max_output_tokens"] == 123
    assert kwargs["temperature"] == 0.2


def test_map_response_maps_text_and_tool_calls() -> None:
    """Test mapping response text and tool calls."""
    client = LLMClient(Mock())

    function_call = SimpleNamespace(
        type="function_call",
        name="my_tool",
        arguments='{"x": 1}',
        call_id="call_123",
    )
    text_item = SimpleNamespace(type="message")

    raw_response = SimpleNamespace(
        output_text="Hello",
        output=[text_item, function_call],
    )

    response = client._map_response(raw_response)

    assert response.text == "Hello"
    assert response.raw is raw_response
    assert response.output_items == [text_item, function_call]
    assert len(response.tool_calls) == 1

    tool_call = response.tool_calls[0]
    assert tool_call.name == "my_tool"
    assert tool_call.arguments == '{"x": 1}'
    assert tool_call.call_id == "call_123"
    assert tool_call.raw is function_call


@pytest.mark.asyncio
async def test_create_response_calls_openai_and_maps_response(
    fake_openai_client: Mock,
) -> None:
    """Test response creation through the OpenAI client."""
    raw_response = SimpleNamespace(output_text="Done", output=[])
    fake_openai_client.responses.create.return_value = raw_response

    client = LLMClient(fake_openai_client)

    response = await client.create_response(
        input_data="Prompt",
        tools=[{"type": "function"}],
        instructions="System instruction",
        max_output_tokens=50,
    )

    fake_openai_client.responses.create.assert_awaited_once()

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    assert call_kwargs["input"] == "Prompt"
    assert call_kwargs["tools"] == [{"type": "function"}]
    assert call_kwargs["instructions"] == "System instruction"
    assert call_kwargs["max_output_tokens"] == 50

    assert response.text == "Done"


@pytest.mark.asyncio
async def test_get_text_response_returns_only_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that text response helper returns only text."""
    client = LLMClient(Mock())
    create_response_mock = AsyncMock(
        return_value=SimpleNamespace(text="Only text"),
    )

    monkeypatch.setattr(client, "create_response", create_response_mock)

    result = await client.get_text_response("Prompt")

    assert result == "Only text"
    create_response_mock.assert_awaited_once_with(
        input_data="Prompt",
        tools=None,
        instructions=None,
        text_format=None,
        max_output_tokens=None,
        temperature=None,
    )


@pytest.mark.asyncio
async def test_stream_response_events_yields_deltas_and_final(
    fake_openai_client: Mock,
) -> None:
    """Test streaming response events with deltas and final response."""
    fake_openai_client.responses.stream.return_value = FakeStream()

    client = LLMClient(fake_openai_client)

    events = [event async for event in client.stream_response_events("Prompt")]

    assert len(events) == 3

    assert events[0].type == "delta"
    assert events[0].delta == "Hel"
    assert events[0].id == "resp_123:1"

    assert events[1].type == "delta"
    assert events[1].delta == "lo"
    assert events[1].id == "resp_123:2"

    assert events[2].type == "final"
    assert events[2].response is not None
    assert events[2].response.text == "Hello"
