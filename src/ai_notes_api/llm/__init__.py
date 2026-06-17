"""LLM package.

This package re-exports the tool registry used to declare model-callable
tools.
"""

from .client import LLMClient
from .embeddings import EmbeddingClient
from .models import LLMMessage, LLMResponse, LLMStreamEvent, LLMToolCall

__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamEvent",
    "LLMToolCall",
    "EmbeddingClient",
]
