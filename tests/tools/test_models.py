"""Tests for tool data models."""

from ai_notes_api.tools.models import ToolSpec

PARAMETERS = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "required": ["value"],
}


def test_to_llm_tool_returns_provider_definition() -> None:
    """Test that a tool spec serializes to a provider tool definition."""

    def handler(value: str) -> str:
        return value

    spec = ToolSpec(
        name="echo",
        description="Echo the value.",
        parameters=PARAMETERS,
        handler=handler,
    )

    assert spec.to_llm_tool() == {
        "type": "function",
        "name": "echo",
        "description": "Echo the value.",
        "parameters": PARAMETERS,
    }


def test_to_llm_tool_excludes_handler() -> None:
    """Test that the serialized definition does not expose the handler."""

    def handler() -> None:
        return None

    spec = ToolSpec(
        name="noop",
        description="Does nothing.",
        parameters={"type": "object", "properties": {}},
        handler=handler,
    )

    assert "handler" not in spec.to_llm_tool()
