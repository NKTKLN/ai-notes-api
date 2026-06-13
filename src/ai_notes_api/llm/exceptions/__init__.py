"""LLM exceptions package.

This package re-exports exceptions raised by LLM tooling.
"""

from .tool import ToolAlreadyRegisteredError, ToolHandlerNotCallableError

__all__ = ["ToolAlreadyRegisteredError", "ToolHandlerNotCallableError"]
