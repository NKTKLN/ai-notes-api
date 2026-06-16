"""Tests for the OpenAI embedding client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from ai_notes_api.llm.embeddings import EmbeddingClient


@pytest.fixture
def fake_openai_client() -> Mock:
    """Return a mocked OpenAI async client.

    Returns:
        Mock: Mocked OpenAI async client.
    """
    fake_client = Mock()

    fake_client.embeddings = Mock()
    fake_client.embeddings.create = AsyncMock()

    return fake_client


@pytest.mark.asyncio
async def test_create_embedding_returns_empty_for_empty_input(
    fake_openai_client: Mock,
) -> None:
    """Test that embedding creation returns an empty list for empty input."""
    client = EmbeddingClient(fake_openai_client)

    result = await client.create_embedding([])

    assert result == []
    fake_openai_client.embeddings.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_embedding_calls_openai(fake_openai_client: Mock) -> None:
    """Test embedding creation through the OpenAI client."""
    fake_openai_client.embeddings.create.return_value = SimpleNamespace(
        data=[
            SimpleNamespace(embedding=[0.1, 0.2]),
            SimpleNamespace(embedding=[0.3, 0.4]),
        ]
    )

    client = EmbeddingClient(fake_openai_client)

    result = await client.create_embedding(["one", "two"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    fake_openai_client.embeddings.create.assert_awaited_once()

    call_kwargs = fake_openai_client.embeddings.create.await_args.kwargs
    assert call_kwargs["input"] == ["one", "two"]
    assert call_kwargs["encoding_format"] == "float"
