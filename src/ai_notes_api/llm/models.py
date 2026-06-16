"""LLM data models module.

This module defines dataclasses representing model responses, tool calls, and
streaming events.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from ai_notes_api.db.models import MessageRole


@dataclass
class LLMToolCall:
    """Tool call requested by the model.

    Attributes:
        name (str): Name of the tool to call.
        arguments (str): JSON-encoded tool arguments.
        call_id (str): Identifier used to correlate the call with its result.
        raw (Any | None): Original tool call object returned by the provider.
    """

    name: str
    arguments: str
    call_id: str
    raw: Any | None = None


@dataclass
class LLMResponse:
    """Normalized response produced by the model.

    Attributes:
        text (str): Generated response text.
        tool_calls (list[LLMToolCall]): Tool calls requested by the model.
        output_items (list[Any]): Raw output items returned by the provider.
        raw (Any | None): Original response object returned by the provider.
    """

    text: str
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    output_items: list[Any] = field(default_factory=list)
    raw: Any | None = None


@dataclass
class LLMMessage:
    """Message used as model input context.

    Attributes:
        role (MessageRole): Message role.
        content (str): Message content.
    """

    role: MessageRole
    content: str


@dataclass
class LLMStreamEvent:
    """Event emitted while streaming a model response.

    Attributes:
        type (Literal["delta", "final"]): Event type, either an incremental
            delta or the final response.
        id (str | None): Optional event identifier.
        delta (str | None): Incremental text chunk for delta events.
        response (LLMResponse | None): Complete response for final events.
    """

    type: Literal["delta", "final"]
    id: str | None = None
    delta: str | None = None
    response: LLMResponse | None = None
