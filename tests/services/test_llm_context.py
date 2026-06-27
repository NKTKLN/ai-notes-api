"""Tests for the LLM context builder."""

from typing import cast
from uuid import UUID

import pytest

from ai_notes_api.core import settings
from ai_notes_api.db.models import DocumentChunk, Message, MessageRole
from ai_notes_api.llm.embeddings import EmbeddingClient
from ai_notes_api.services.document_chunk import DocumentChunkService
from ai_notes_api.services.llm_context import LLMContextBuilder
from ai_notes_api.services.message import MessageService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_DOCUMENT_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeEmbeddingClient:
    """Fake embedding client recording embedded texts for context testing."""

    def __init__(self) -> None:
        """Initialize the fake embedding client."""
        self.embedded_texts: list[str] | None = None
        self.embedding: list[float] = [0.1, 0.2, 0.3]

    async def create_embedding(self, texts: list[str]) -> list[list[float]]:
        """Record the texts and return one embedding vector per text."""
        self.embedded_texts = texts
        return [self.embedding for _ in texts]


class FakeMessageService:
    """Fake message service returning preconfigured context messages."""

    def __init__(self) -> None:
        """Initialize the fake message service."""
        self.context_messages: list[Message] = []
        self.context_limit: int | None = None

    async def get_context_messages(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        limit: int,
    ) -> list[Message]:
        """Record the limit and return the configured context messages."""
        self.context_limit = limit
        return self.context_messages


class FakeDocumentChunkService:
    """Fake document chunk service recording vector searches for context testing."""

    def __init__(self) -> None:
        """Initialize the fake document chunk service."""
        self.chunks: list[DocumentChunk] = []
        self.search_query_embedding: list[float] | None = None

    async def vector_search(
        self,
        user_id: UUID,  # noqa: ARG002
        session_id: UUID,  # noqa: ARG002
        query_embedding: list[float],
        top_k: int = 5,  # noqa: ARG002
    ) -> list[DocumentChunk]:
        """Record the query embedding and return the configured chunks."""
        self.search_query_embedding = query_embedding
        return self.chunks


def _build_builder() -> tuple[
    FakeEmbeddingClient,
    FakeMessageService,
    FakeDocumentChunkService,
    LLMContextBuilder,
]:
    """Build an LLM context builder wired with fakes."""
    embeddings = FakeEmbeddingClient()
    messages = FakeMessageService()
    chunks = FakeDocumentChunkService()

    builder = LLMContextBuilder(
        embeddings=cast(EmbeddingClient, embeddings),
        message_service=cast(MessageService, messages),
        chunk_service=cast(DocumentChunkService, chunks),
    )

    return embeddings, messages, chunks, builder


def _message(content: str) -> Message:
    """Return a user message with the given content."""
    return Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content=content,
        role=MessageRole.USER,
    )


@pytest.mark.asyncio
async def test_build_embeds_question_and_searches_chunks() -> None:
    """Test that the question is embedded and used for chunk vector search."""
    embeddings, _messages, chunks, builder = _build_builder()

    await builder.build(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        question="What is RAG?",
    )

    assert embeddings.embedded_texts == ["What is RAG?"]
    assert chunks.search_query_embedding == embeddings.embedding


@pytest.mark.asyncio
async def test_build_includes_all_context_messages() -> None:
    """Test that every provided context message is kept in the memory context.

    The current turn is excluded by the caller (context is fetched before the
    turn is persisted), so the builder uses the context as-is.
    """
    _embeddings, messages, _chunks, builder = _build_builder()
    messages.context_messages = [_message("First message"), _message("Second message")]

    result = await builder.build(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        question="My question",
    )

    contents = [str(item.get("content", "")) for item in result]
    assert any("First message" in content for content in contents)
    assert any("Second message" in content for content in contents)
    # The question is added once via RAG, not duplicated.
    assert sum(content == "My question" for content in contents) == 1


@pytest.mark.asyncio
async def test_build_includes_chunks_and_question() -> None:
    """Test that retrieved chunks and the question are present in the prompt."""
    _embeddings, _messages, chunks, builder = _build_builder()
    chunks.chunks = [
        DocumentChunk(document_id=TEST_DOCUMENT_ID, content="Relevant chunk"),
    ]

    result = await builder.build(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        question="My question",
    )

    contents = [str(item.get("content", "")) for item in result]
    assert any("Relevant chunk" in content for content in contents)
    assert any(content == "My question" for content in contents)


@pytest.mark.asyncio
async def test_build_uses_configured_context_limit() -> None:
    """Test that the configured context message limit is forwarded."""
    _embeddings, messages, _chunks, builder = _build_builder()

    await builder.build(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        question="Question",
    )

    assert messages.context_limit == settings.llm_context_messages_limit
