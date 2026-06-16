"""Tests for the tool registry."""

import json

import pytest

from ai_notes_api.tools.exceptions import (
    ToolAlreadyRegisteredError,
    ToolHandlerNotCallableError,
)
from ai_notes_api.tools.registry import ToolRegistry

PARAMETERS = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "required": ["value"],
}


def _echo(value: str) -> str:
    """Return the provided value unchanged."""
    return value


def test_register_adds_tool_to_serialized_tools() -> None:
    """Test that a registered tool appears in the serialized tool list."""
    registry = ToolRegistry()

    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    tools = registry.get_tools()

    assert len(tools) == 1
    assert tools[0] == {
        "type": "function",
        "name": "echo",
        "description": "Echo the value.",
        "parameters": PARAMETERS,
    }


def test_get_tools_returns_empty_list_when_no_tools() -> None:
    """Test that an empty registry serializes to an empty tool list."""
    registry = ToolRegistry()

    assert registry.get_tools() == []


def test_register_duplicate_name_raises() -> None:
    """Test that registering a duplicate tool name raises an error."""
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    with pytest.raises(ToolAlreadyRegisteredError) as exc_info:
        registry.register(
            name="echo",
            description="Another echo.",
            parameters=PARAMETERS,
            handler=_echo,
        )

    assert exc_info.value.name == "echo"


def test_register_non_callable_handler_raises() -> None:
    """Test that registering a non-callable handler raises an error."""
    registry = ToolRegistry()

    with pytest.raises(ToolHandlerNotCallableError) as exc_info:
        registry.register(
            name="echo",
            description="Echo the value.",
            parameters=PARAMETERS,
            handler="not-callable",  # type: ignore[arg-type]
        )

    assert exc_info.value.name == "echo"
    assert registry.get_tools() == []


@pytest.mark.asyncio
async def test_call_sync_handler_returns_success_payload() -> None:
    """Test that calling a sync handler returns an ok payload with the result."""
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    result = json.loads(await registry.call("echo", json.dumps({"value": "hi"})))

    assert result == {"ok": True, "data": "hi", "error": None}


@pytest.mark.asyncio
async def test_call_async_handler_is_awaited() -> None:
    """Test that an async handler is awaited and its result returned."""

    async def async_echo(value: str) -> str:
        return value.upper()

    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=async_echo,
    )

    result = json.loads(await registry.call("echo", json.dumps({"value": "hi"})))

    assert result == {"ok": True, "data": "HI", "error": None}


@pytest.mark.asyncio
async def test_call_unknown_tool_returns_error() -> None:
    """Test that calling an unregistered tool returns an error payload."""
    registry = ToolRegistry()

    result = json.loads(await registry.call("missing", json.dumps({})))

    assert result["ok"] is False
    assert result["data"] is None
    assert "Unknown tool: missing" in result["error"]


@pytest.mark.asyncio
async def test_call_with_invalid_json_returns_error() -> None:
    """Test that invalid JSON arguments return an error payload."""
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    result = json.loads(await registry.call("echo", "not-json"))

    assert result["ok"] is False
    assert result["data"] is None
    assert result["error"]


@pytest.mark.asyncio
async def test_call_with_non_object_arguments_returns_error() -> None:
    """Test that non-object JSON arguments return an error payload."""
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    result = json.loads(await registry.call("echo", json.dumps(["value"])))

    assert result["ok"] is False
    assert result["error"] == "Tool arguments must be a JSON object"


@pytest.mark.asyncio
async def test_call_handler_exception_is_captured() -> None:
    """Test that handler exceptions are captured as error payloads."""

    def boom(value: str) -> str:  # noqa: ARG001
        raise RuntimeError("kaboom")

    registry = ToolRegistry()
    registry.register(
        name="boom",
        description="Always fails.",
        parameters=PARAMETERS,
        handler=boom,
    )

    result = json.loads(await registry.call("boom", json.dumps({"value": "x"})))

    assert result["ok"] is False
    assert result["data"] is None
    assert "kaboom" in result["error"]


@pytest.mark.asyncio
async def test_call_preserves_non_ascii_output() -> None:
    """Test that non-ASCII handler output is preserved in the payload."""
    registry = ToolRegistry()
    registry.register(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=_echo,
    )

    raw = await registry.call("echo", json.dumps({"value": "Привет"}))

    assert "Привет" in raw
    assert json.loads(raw)["data"] == "Привет"
