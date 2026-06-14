"""LLM package.

This package re-exports the tool registry used to declare model-callable
tools.
"""

from .client import LLMClient
from .models import LLMResponse, LLMStreamEvent, LLMToolCall

__all__ = ["LLMClient", "LLMResponse", "LLMStreamEvent", "LLMToolCall"]
