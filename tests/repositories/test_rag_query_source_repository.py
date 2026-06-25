"""Tests for RAG query source repository."""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import (
    ChatSession,
    Document,
    DocumentChunk,
    DocumentStatus,
    RagQuery,
    RagQuerySource,
    RagQueryStatus,
    User,
)
from ai_notes_api.repositories.rag_query_source import RagQuerySourceRepository

EMBEDDING_DIM = 1536


@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


async def create_rag_query(
    async_session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> RagQuery:
    """Persist a RAG query for RAG query source repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the RAG query.
        session_id (UUID): Identifier of the chat session that owns the RAG query.

    Returns:
        RagQuery: Persisted RAG query instance.
    """
    rag_query = RagQuery(
        user_id=user_id,
        session_id=session_id,
        question="What is RAG?",
        top_k=5,
        status=RagQueryStatus.COMPLETED,
    )

    async_session.add(rag_query)
    await async_session.flush()
    await async_session.refresh(rag_query)

    return rag_query


async def create_document_with_chunk(
    async_session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> tuple[Document, DocumentChunk]:
    """Persist a document and a chunk for RAG query source repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the rows.
        user_id (UUID): Identifier of the user who owns the rows.
        session_id (UUID): Identifier of the chat session that owns the rows.

    Returns:
        tuple[Document, DocumentChunk]: Persisted document and chunk instances.
    """
    document = Document(
        user_id=user_id,
        session_id=session_id,
        filename="test.pdf",
        content_type="application/pdf",
        file_size=1024,
        checksum_sha256="checksum",
        storage_bucket="documents",
        storage_object_name="object",
        status=DocumentStatus.READY,
    )

    async_session.add(document)
    await async_session.flush()
    await async_session.refresh(document)

    chunk = DocumentChunk(
        user_id=user_id,
        session_id=session_id,
        document_id=document.id,
        chunk_index=0,
        content="chunk content",
        content_hash="hash",
        embedding=[0.0] * EMBEDDING_DIM,
        embedding_model="text-embedding-3-small",
    )

    async_session.add(chunk)
    await async_session.flush()
    await async_session.refresh(chunk)

    return document, chunk


def create_source(
    *,
    rag_query_id: UUID,
    document_id: UUID,
    chunk_id: UUID,
    rank: int = 1,
    score: float = 0.9,
) -> RagQuerySource:
    """Create a RAG query source instance for repository tests.

    Args:
        rag_query_id (UUID): Identifier of the RAG query the source belongs to.
        document_id (UUID): Identifier of the source document.
        chunk_id (UUID): Identifier of the source document chunk.
        rank (int): Rank of the chunk among the retrieved sources.
        score (float): Relevance score of the chunk for the query.

    Returns:
        RagQuerySource: RAG query source model instance.
    """
    return RagQuerySource(
        rag_query_id=rag_query_id,
        document_id=document_id,
        chunk_id=chunk_id,
        rank=rank,
        score=score,
        content_preview="preview",
    )


@pytest.mark.asyncio
async def test_create_source_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful RAG query source creation."""
    repository = RagQuerySourceRepository(session=async_session)

    chat_session = ChatSession(user_id=test_user.id, title="Test chat session")
    async_session.add(chat_session)
    await async_session.flush()

    rag_query = await create_rag_query(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )
    document, chunk = await create_document_with_chunk(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    source = await repository.create(
        create_source(
            rag_query_id=rag_query.id,
            document_id=document.id,
            chunk_id=chunk.id,
        )
    )

    assert source.id is not None
    assert source.rag_query_id == rag_query.id
    assert source.document_id == document.id
    assert source.chunk_id == chunk.id


@pytest.mark.asyncio
async def test_create_many_sources_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful bulk RAG query source creation."""
    repository = RagQuerySourceRepository(session=async_session)

    chat_session = ChatSession(user_id=test_user.id, title="Test chat session")
    async_session.add(chat_session)
    await async_session.flush()

    rag_query = await create_rag_query(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )
    document, chunk = await create_document_with_chunk(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    sources = await repository.create_many(
        [
            create_source(
                rag_query_id=rag_query.id,
                document_id=document.id,
                chunk_id=chunk.id,
                rank=rank,
            )
            for rank in range(1, 4)
        ]
    )

    assert len(sources) == 3
    assert all(source.id is not None for source in sources)


@pytest.mark.asyncio
async def test_get_list_for_rag_query_orders_by_rank_asc(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that sources list is ordered by rank in ascending order."""
    repository = RagQuerySourceRepository(session=async_session)

    chat_session = ChatSession(user_id=test_user.id, title="Test chat session")
    async_session.add(chat_session)
    await async_session.flush()

    rag_query = await create_rag_query(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )
    document, chunk = await create_document_with_chunk(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    await repository.create_many(
        [
            create_source(
                rag_query_id=rag_query.id,
                document_id=document.id,
                chunk_id=chunk.id,
                rank=rank,
            )
            for rank in (3, 1, 2)
        ]
    )

    sources = await repository.get_list_for_rag_query(rag_query.id)

    assert [source.rank for source in sources] == [1, 2, 3]


@pytest.mark.asyncio
async def test_get_list_for_rag_query_scoped_to_rag_query(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that sources list is scoped to the requested RAG query."""
    repository = RagQuerySourceRepository(session=async_session)

    chat_session = ChatSession(user_id=test_user.id, title="Test chat session")
    async_session.add(chat_session)
    await async_session.flush()

    document, chunk = await create_document_with_chunk(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    first_query = await create_rag_query(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )
    second_query = await create_rag_query(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    owned = await repository.create(
        create_source(
            rag_query_id=first_query.id,
            document_id=document.id,
            chunk_id=chunk.id,
        )
    )
    await repository.create(
        create_source(
            rag_query_id=second_query.id,
            document_id=document.id,
            chunk_id=chunk.id,
        )
    )

    sources = await repository.get_list_for_rag_query(first_query.id)

    assert len(sources) == 1
    assert sources[0].id == owned.id
