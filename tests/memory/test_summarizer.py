"""Tests for the memory summarizer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import MessageRole
from ai_notes_api.llm.models import LLMMessage
from ai_notes_api.memory.prompts import SUMMARY_PROMPT
from ai_notes_api.memory.summarizer import MemorySummarizer


@pytest.fixture
def fake_openai_client() -> Mock:
    """Return a mocked OpenAI async client.

    Returns:
        Mock: Mocked OpenAI async client with a mocked responses API.
    """
    fake_client = Mock()

    fake_client.responses = Mock()
    fake_client.responses.create = AsyncMock()

    return fake_client


def _context_messages() -> list[LLMMessage]:
    """Return sample context messages for summarizer tests.

    Returns:
        list[LLMMessage]: Source transcript messages.
    """
    return [
        LLMMessage(role=MessageRole.USER, content="I work as a developer"),
        LLMMessage(role=MessageRole.ASSISTANT, content="Got it"),
    ]


@pytest.mark.asyncio
async def test_summarize_returns_stripped_output(fake_openai_client: Mock) -> None:
    """Test that the updated summary is returned stripped of whitespace."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text="  Updated summary.  "
    )

    summarizer = MemorySummarizer(fake_openai_client)

    result = await summarizer.summarize(
        summary="Old summary.",
        context_messages=_context_messages(),
    )

    assert result == "Updated summary."


@pytest.mark.asyncio
async def test_summarize_passes_prompt_and_settings(fake_openai_client: Mock) -> None:
    """Test that summarization forwards the prompt, model, and token limits."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Summary."
    )

    summarizer = MemorySummarizer(fake_openai_client)

    await summarizer.summarize(
        summary="Old summary.",
        context_messages=_context_messages(),
    )

    fake_openai_client.responses.create.assert_awaited_once()

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    assert call_kwargs["instructions"] == SUMMARY_PROMPT
    assert call_kwargs["model"] == settings.open_ai_model
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["max_output_tokens"] == 500


@pytest.mark.asyncio
async def test_summarize_includes_summary_and_transcript(
    fake_openai_client: Mock,
) -> None:
    """Test that the input contains the existing summary and the transcript."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Summary."
    )

    summarizer = MemorySummarizer(fake_openai_client)

    await summarizer.summarize(
        summary="Old summary.",
        context_messages=_context_messages(),
    )

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    summary_message, transcript_message = call_kwargs["input"]

    assert "Old summary." in summary_message["content"]
    assert "I work as a developer" in transcript_message["content"]


@pytest.mark.asyncio
async def test_summarize_uses_placeholder_for_empty_summary(
    fake_openai_client: Mock,
) -> None:
    """Test that a blank summary falls back to the no-summary placeholder."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Summary."
    )

    summarizer = MemorySummarizer(fake_openai_client)

    await summarizer.summarize(
        summary="   ",
        context_messages=_context_messages(),
    )

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    summary_message = call_kwargs["input"][0]

    assert "No previous summary." in summary_message["content"]
