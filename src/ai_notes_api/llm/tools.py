"""Tool registry module.

This module provides a registry for declaring callable tools that the model
can invoke and for dispatching tool calls to their handlers.
"""

import json
from collections.abc import Callable
from typing import Any

from ai_notes_api.llm.exceptions import (
    ToolAlreadyRegisteredError,
    ToolHandlerNotCallableError,
)
from ai_notes_api.llm.models import ToolSpec


class ToolRegistry:
    """Registry for model-callable tools and their handlers."""

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Register a tool and its handler.

        Args:
            name (str): Unique tool name.
            description (str): Human-readable description of the tool.
            parameters (dict[str, Any]): JSON schema describing the tool parameters.
            handler (Callable[..., Any]): Callable invoked when the tool is called.

        Raises:
            ToolAlreadyRegisteredError: If a tool with the same name is already
                registered.
            ToolHandlerNotCallableError: If the provided handler is not callable.
        """
        if name in self._tools:
            raise ToolAlreadyRegisteredError(name)

        if not callable(handler):
            raise ToolHandlerNotCallableError(name)

        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

    def call(self, name: str, arguments: str) -> str:
        """Call a registered tool with JSON-encoded arguments.

        Args:
            name (str): Name of the tool to call.
            arguments (str): JSON-encoded object of tool arguments.

        Returns:
            str: JSON-encoded result containing the handler output on success
            or an error message on failure.
        """
        if name not in self._tools:
            return self._make_error(f"Unknown tool: {name}")

        try:
            parsed_arguments = json.loads(arguments)

            if not isinstance(parsed_arguments, dict):
                return self._make_error("Tool arguments must be a JSON object")

            result = self._tools[name].handler(**parsed_arguments)

            return json.dumps(
                {
                    "ok": True,
                    "data": result,
                    "error": None,
                },
                ensure_ascii=False,
            )

        except Exception as error:
            return self._make_error(str(error))

    def _make_error(self, message: str) -> str:
        """Build a JSON-encoded error result.

        Args:
            message (str): Error message to include in the result.

        Returns:
            str: JSON-encoded error result.
        """
        return json.dumps(
            {
                "ok": False,
                "data": None,
                "error": message,
            },
            ensure_ascii=False,
        )
