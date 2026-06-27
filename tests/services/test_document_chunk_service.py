"""Tests for the document chunk service."""

from typing import cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import DocumentChunk
from ai_notes_api.repositories import DocumentChunkRepository
from ai_notes_api.services.document_chunk import DocumentChunkService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_DOCUMENT_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeDocumentChunkRepository:
    """Fake chunk repository recording vector search calls for service testing."""

    def __init__(self) -> None:
        """Initialize the fake chunk repository."""
        self.chunks: list[DocumentChunk] = []
        self.query_embedding: list[float] | None = None
        self.user_id: UUID | None = None
        self.session_id: UUID | None = None
        self.top_k: int | None = None

    async def vector_search_in_user_session(
        self,
        query_embedding: list[float],
        user_id: UUID,
        session_id: UUID,
        top_k: int = 5,
    ) -> list[DocumentChunk]:
        """Record the search parameters and return the configured chunks."""
        self.query_embedding = query_embedding
        self.user_id = user_id
        self.session_id = session_id
        self.top_k = top_k
        return self.chunks


@pytest.mark.asyncio
async def test_vector_search_forwards_arguments_to_repository() -> None:
    """Test that the service forwards search arguments to the repository."""
    repository = FakeDocumentChunkRepository()
    service = DocumentChunkService(
        chunk_repository=cast(DocumentChunkRepository, repository),
    )

    await service.vector_search(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        query_embedding=[0.1, 0.2, 0.3],
        top_k=7,
    )

    assert repository.query_embedding == [0.1, 0.2, 0.3]
    assert repository.user_id == TEST_USER_ID
    assert repository.session_id == TEST_SESSION_ID
    assert repository.top_k == 7


@pytest.mark.asyncio
async def test_vector_search_uses_default_top_k() -> None:
    """Test that the default top_k is forwarded when none is provided."""
    repository = FakeDocumentChunkRepository()
    service = DocumentChunkService(
        chunk_repository=cast(DocumentChunkRepository, repository),
    )

    await service.vector_search(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        query_embedding=[0.1],
    )

    assert repository.top_k == 5


@pytest.mark.asyncio
async def test_vector_search_returns_repository_chunks() -> None:
    """Test that the service returns the chunks produced by the repository."""
    repository = FakeDocumentChunkRepository()
    repository.chunks = [
        DocumentChunk(document_id=TEST_DOCUMENT_ID, content="chunk"),
    ]
    service = DocumentChunkService(
        chunk_repository=cast(DocumentChunkRepository, repository),
    )

    result = await service.vector_search(
        user_id=TEST_USER_ID,
        session_id=TEST_SESSION_ID,
        query_embedding=[0.1],
    )

    assert result == repository.chunks
