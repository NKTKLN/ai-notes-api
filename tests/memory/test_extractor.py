"""Tests for the memory fact extractor."""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import MessageRole
from ai_notes_api.llm.models import LLMMessage
from ai_notes_api.memory.extractor import MemoryExtractor
from ai_notes_api.memory.prompts import FACT_EXTRACTION_PROMPT


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
    """Return sample context messages for extractor tests.

    Returns:
        list[LLMMessage]: Source transcript messages.
    """
    return [
        LLMMessage(role=MessageRole.USER, content="My name is Alex"),
        LLMMessage(role=MessageRole.ASSISTANT, content="Nice to meet you"),
    ]


@pytest.mark.asyncio
async def test_extract_parses_structured_output(fake_openai_client: Mock) -> None:
    """Test that extraction parses the structured JSON output."""
    expected: dict[str, list[dict[str, Any]]] = {
        "facts": [
            {
                "key": "name",
                "value": "Alex",
                "confidence": 1.0,
                "source_text": "My name is Alex",
            }
        ]
    }
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(expected)
    )

    extractor = MemoryExtractor(fake_openai_client)

    result = await extractor.extract(facts=[], context_messages=_context_messages())

    assert result == expected


@pytest.mark.asyncio
async def test_extract_passes_schema_and_settings(fake_openai_client: Mock) -> None:
    """Test that extraction forwards the prompt, model, schema, and temperature."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text='{"facts": []}'
    )

    extractor = MemoryExtractor(fake_openai_client)

    await extractor.extract(facts=[], context_messages=_context_messages())

    fake_openai_client.responses.create.assert_awaited_once()

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    assert call_kwargs["instructions"] == FACT_EXTRACTION_PROMPT
    assert call_kwargs["model"] == settings.open_ai_model
    assert call_kwargs["text"] == {"format": MemoryExtractor.FACTS_SCHEMA}
    assert call_kwargs["temperature"] == 0


@pytest.mark.asyncio
async def test_extract_builds_input_with_facts_and_transcript(
    fake_openai_client: Mock,
) -> None:
    """Test that the input includes existing facts and the transcript."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text='{"facts": []}'
    )

    facts = [{"key": "city", "value": "Berlin"}]

    extractor = MemoryExtractor(fake_openai_client)

    await extractor.extract(facts=facts, context_messages=_context_messages())

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    input_messages = call_kwargs["input"]

    facts_message, transcript_message = input_messages

    assert json.dumps(facts, ensure_ascii=False, indent=2) in facts_message["content"]
    assert "My name is Alex" in transcript_message["content"]
    assert 'role="user"' in transcript_message["content"]


@pytest.mark.asyncio
async def test_extract_uses_empty_list_placeholder_for_no_facts(
    fake_openai_client: Mock,
) -> None:
    """Test that an empty fact list is rendered as an empty JSON array."""
    fake_openai_client.responses.create.return_value = SimpleNamespace(
        output_text='{"facts": []}'
    )

    extractor = MemoryExtractor(fake_openai_client)

    await extractor.extract(facts=[], context_messages=_context_messages())

    call_kwargs = fake_openai_client.responses.create.await_args.kwargs
    facts_message = call_kwargs["input"][0]

    assert "<existing_facts>[]</existing_facts>" in facts_message["content"]
