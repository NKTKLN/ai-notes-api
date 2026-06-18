"""Tests for the memory prompt builder."""

import json

from ai_notes_api.db.models import MessageRole
from ai_notes_api.llm.models import LLMMessage
from ai_notes_api.memory.prompt_builder import PromptBuilder


def _context_messages() -> list[LLMMessage]:
    """Return sample context messages for prompt builder tests.

    Returns:
        list[LLMMessage]: Context messages used as conversational context.
    """
    return [
        LLMMessage(role=MessageRole.USER, content="Hello"),
        LLMMessage(role=MessageRole.ASSISTANT, content="Hi there"),
    ]


def test_build_includes_memory_message_and_context() -> None:
    """Test that the built prompt starts with a memory message and keeps context."""
    facts = [{"key": "name", "value": "Alex"}]

    llm_messages = PromptBuilder.build(
        context_messages=_context_messages(),
        facts=facts,
        summary="Previous summary.",
    )

    assert len(llm_messages) == 3

    memory_message = llm_messages[0]
    assert memory_message["role"] == "user"
    assert "Previous summary." in memory_message["content"]
    assert json.dumps(facts, ensure_ascii=False, indent=2) in memory_message["content"]

    assert llm_messages[1]["role"] == MessageRole.USER
    assert llm_messages[1]["content"] == "Hello"
    assert llm_messages[2]["role"] == MessageRole.ASSISTANT
    assert llm_messages[2]["content"] == "Hi there"


def test_build_without_facts_uses_empty_list_placeholder() -> None:
    """Test that missing facts are rendered as an empty JSON array."""
    llm_messages = PromptBuilder.build(
        context_messages=_context_messages(),
        facts=None,
        summary="Summary.",
    )

    assert "<known_facts>\n[]\n</known_facts>" in llm_messages[0]["content"]


def test_build_with_empty_summary_uses_placeholder() -> None:
    """Test that a blank summary falls back to the no-summary placeholder."""
    llm_messages = PromptBuilder.build(
        context_messages=_context_messages(),
        facts=None,
        summary="   ",
    )

    assert "No previous summary." in llm_messages[0]["content"]


def test_build_with_empty_context_returns_only_memory_message() -> None:
    """Test that an empty context yields a prompt with only the memory message."""
    llm_messages = PromptBuilder.build(
        context_messages=[],
        facts=None,
        summary="",
    )

    assert len(llm_messages) == 1
    assert llm_messages[0]["role"] == "user"
