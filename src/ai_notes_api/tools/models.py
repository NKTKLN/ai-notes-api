"""Tool data models module.

This module defines the dataclass describing a registered tool and its
conversion to a provider tool definition.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

type SyncToolHandler = Callable[..., Any]
type AsyncToolHandler = Callable[..., Awaitable[Any]]
type ToolHandler = SyncToolHandler | AsyncToolHandler


@dataclass
class ToolSpec:
    """Specification of a registered tool.

    Attributes:
        name (str): Unique tool name.
        description (str): Human-readable description of the tool.
        parameters (dict[str, Any]): JSON schema describing the tool parameters.
        handler (ToolHandler): Callable invoked when the tool is called.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def to_llm_tool(self) -> dict[str, Any]:
        """Convert the tool specification to a provider tool definition.

        Returns:
            dict[str, Any]: Tool definition formatted for the LLM provider.
        """
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
