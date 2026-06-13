"""LLM exceptions package.

This package re-exports exceptions raised by LLM tooling.
"""

from .llm import LLMDisabledError
from .tool import ToolAlreadyRegisteredError, ToolHandlerNotCallableError

__all__ = [
    "LLMDisabledError",
    "ToolAlreadyRegisteredError",
    "ToolHandlerNotCallableError",
]
