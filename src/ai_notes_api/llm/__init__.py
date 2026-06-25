"""LLM package.

This package re-exports the tool registry used to declare model-callable
tools.
"""

from ai_notes_api.llm.client import LLMClient
from ai_notes_api.llm.embeddings import EmbeddingClient
from ai_notes_api.llm.schemas import (
    LLMMessage,
    LLMResponse,
    LLMStreamEvent,
    LLMToolCall,
)

__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamEvent",
    "LLMToolCall",
    "EmbeddingClient",
]
