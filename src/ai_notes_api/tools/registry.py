"""Tool registry module.

This module provides a registry for declaring callable tools that the model
can invoke and for dispatching tool calls to their handlers.
"""

import json
from inspect import isawaitable
from typing import Any

from loguru import logger

from ai_notes_api.tools.exceptions import (
    ToolAlreadyRegisteredError,
)
from ai_notes_api.tools.models import ToolHandler, ToolSpec


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
        handler: ToolHandler,
    ) -> None:
        """Register a tool and its handler.

        Args:
            name (str): Unique tool name.
            description (str): Human-readable description of the tool.
            parameters (dict[str, Any]): JSON schema describing the tool parameters.
            handler (ToolHandler): Callable invoked when the tool is called.

        Raises:
            ToolAlreadyRegisteredError: If a tool with the same name is already
                registered.
            ToolHandlerNotCallableError: If the provided handler is not callable.
        """
        if name in self._tools:
            logger.warning("Tool already registered: name={}", name)
            raise ToolAlreadyRegisteredError(name)

        self._tools[name] = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

        logger.info("Tool registered: name={}", name)

    def get_tools(self) -> list[dict[str, Any]]:
        """Return registered tools serialized for the LLM provider.

        Returns:
            list[dict[str, Any]]: Registered tool definitions.
        """
        tools: list[dict[str, Any]] = []

        for tool in self._tools.values():
            tools.append(tool.to_llm_tool())

        return tools

    async def call(self, name: str, arguments: str) -> str:
        """Call a registered tool with JSON-encoded arguments.

        Args:
            name (str): Name of the tool to call.
            arguments (str): JSON-encoded object of tool arguments.

        Returns:
            str: JSON-encoded result containing the handler output on success
            or an error message on failure.
        """
        if name not in self._tools:
            logger.warning("Tool call for unknown tool: name={}", name)
            return self._make_error(f"Unknown tool: {name}")

        logger.debug("Tool call started: name={}", name)

        try:
            parsed_arguments = json.loads(arguments)

            if not isinstance(parsed_arguments, dict):
                logger.warning("Tool arguments are not a JSON object: name={}", name)
                return self._make_error("Tool arguments must be a JSON object")

            handler = self._tools[name].handler
            result = handler(**parsed_arguments)

            if isawaitable(result):
                result = await result

            logger.info("Tool call succeeded: name={}", name)

            return json.dumps(
                {
                    "ok": True,
                    "data": result,
                    "error": None,
                },
                ensure_ascii=False,
            )

        except Exception as error:
            logger.exception("Tool call failed: name={}", name)
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
