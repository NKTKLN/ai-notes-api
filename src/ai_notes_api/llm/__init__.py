"""LLM package.

This package re-exports the tool registry used to declare model-callable
tools.
"""

from .tools import ToolRegistry
from .client import LLMClient

__all__ = ["ToolRegistry", "LLMClient"]
