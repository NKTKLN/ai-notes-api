"""Tests for document chunk repository."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import (
    ChatSession,
    Document,
    DocumentChunk,
    DocumentStatus,
    User,
)
from ai_notes_api.repositories.document_chunk import DocumentChunkRepository

EMBEDDING_DIM = 1536


def make_embedding(*, first: float = 0.0, second: float = 0.0) -> list[float]:
    """Build a fixed-size embedding with the first two components set.

    Args:
        first (float): Value of the first embedding component.
        second (float): Value of the second embedding component.

    Returns:
        list[float]: Embedding vector of length ``EMBEDDING_DIM``.
    """
    embedding = [0.0] * EMBEDDING_DIM
    embedding[0] = first
    embedding[1] = second

    return embedding


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


@pytest_asyncio.fixture
async def other_user(async_session: AsyncSession) -> User:
    """Create another test user."""
    user = User(
        email="other-user@example.com",
        username="other_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


async def create_chat_session(
    async_session: AsyncSession,
    *,
    user_id: UUID,
) -> ChatSession:
    """Persist a chat session for document chunk repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the chat session.

    Returns:
        ChatSession: Persisted chat session instance.
    """
    chat_session = ChatSession(user_id=user_id, title="Test chat session")

    async_session.add(chat_session)
    await async_session.flush()
    await async_session.refresh(chat_session)

    return chat_session


async def create_document(
    async_session: AsyncSession,
    *,
    user_id: UUID,
    session_id: UUID,
) -> Document:
    """Persist a document for document chunk repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the document.
        session_id (UUID): Identifier of the chat session that owns the document.

    Returns:
        Document: Persisted document instance.
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

    return document


def create_chunk(  # noqa: PLR0913
    *,
    user_id: UUID,
    session_id: UUID,
    document_id: UUID,
    chunk_index: int = 0,
    content: str = "chunk content",
    embedding: list[float] | None = None,
) -> DocumentChunk:
    """Create a document chunk instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the chunk.
        session_id (UUID): Identifier of the chat session that owns the chunk.
        document_id (UUID): Identifier of the document the chunk belongs to.
        chunk_index (int): Position of the chunk within the document.
        content (str): Text content of the chunk.
        embedding (list[float] | None): Optional embedding vector.

    Returns:
        DocumentChunk: Document chunk model instance.
    """
    return DocumentChunk(
        user_id=user_id,
        session_id=session_id,
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        content_hash=f"hash-{chunk_index}",
        embedding=embedding if embedding is not None else make_embedding(first=1.0),
        embedding_model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_create_chunk_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document chunk creation."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    chunk = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
        )
    )

    assert chunk.id is not None
    assert chunk.document_id == document.id


@pytest.mark.asyncio
async def test_create_many_chunks_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful bulk document chunk creation."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    chunks = await repository.create_many(
        [
            create_chunk(
                user_id=test_user.id,
                session_id=chat_session.id,
                document_id=document.id,
                chunk_index=index,
            )
            for index in range(3)
        ]
    )

    assert len(chunks) == 3
    assert all(chunk.id is not None for chunk in chunks)


@pytest.mark.asyncio
async def test_get_by_id_chunk_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document chunk retrieval by identifier."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    created = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
        )
    )

    chunk = await repository.get_by_id(created.id)

    assert chunk is not None
    assert chunk.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_chunk_not_found(async_session: AsyncSession) -> None:
    """Test that document chunk retrieval by identifier returns None when missing."""
    repository = DocumentChunkRepository(session=async_session)

    chunk = await repository.get_by_id(uuid4())

    assert chunk is None


@pytest.mark.asyncio
async def test_search_in_user_session_orders_by_similarity(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that search returns chunks ordered by cosine distance to the query."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    near = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
            chunk_index=0,
            content="near",
            embedding=make_embedding(first=1.0),
        )
    )
    far = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
            chunk_index=1,
            content="far",
            embedding=make_embedding(second=1.0),
        )
    )

    results = await repository.vector_search_in_user_session(
        query_embedding=make_embedding(first=1.0),
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    assert [chunk.id for chunk in results] == [near.id, far.id]


@pytest.mark.asyncio
async def test_search_in_user_session_respects_top_k(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that search limits the number of returned chunks to top_k."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    await repository.create_many(
        [
            create_chunk(
                user_id=test_user.id,
                session_id=chat_session.id,
                document_id=document.id,
                chunk_index=index,
            )
            for index in range(3)
        ]
    )

    results = await repository.vector_search_in_user_session(
        query_embedding=make_embedding(first=1.0),
        user_id=test_user.id,
        session_id=chat_session.id,
        top_k=2,
    )

    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_in_user_session_scoped_to_user_and_session(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that search is scoped to the requested user and chat session."""
    repository = DocumentChunkRepository(session=async_session)

    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    owned_document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=owned_session.id,
    )
    owned = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=owned_session.id,
            document_id=owned_document.id,
        )
    )

    other_session = await create_chat_session(async_session, user_id=other_user.id)
    other_document = await create_document(
        async_session,
        user_id=other_user.id,
        session_id=other_session.id,
    )
    await repository.create(
        create_chunk(
            user_id=other_user.id,
            session_id=other_session.id,
            document_id=other_document.id,
        )
    )

    results = await repository.vector_search_in_user_session(
        query_embedding=make_embedding(first=1.0),
        user_id=test_user.id,
        session_id=owned_session.id,
    )

    assert len(results) == 1
    assert results[0].id == owned.id


@pytest.mark.asyncio
async def test_search_in_user_session_excludes_soft_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that search ignores soft-deleted chunks."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    chunk = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
        )
    )
    chunk.deleted_at = datetime.now(UTC)
    await repository.update(chunk)

    results = await repository.vector_search_in_user_session(
        query_embedding=make_embedding(first=1.0),
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    assert results == []


@pytest.mark.asyncio
async def test_update_chunk_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document chunk update."""
    repository = DocumentChunkRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)
    document = await create_document(
        async_session,
        user_id=test_user.id,
        session_id=chat_session.id,
    )

    chunk = await repository.create(
        create_chunk(
            user_id=test_user.id,
            session_id=chat_session.id,
            document_id=document.id,
            content="original",
        )
    )

    chunk.content = "updated"

    updated = await repository.update(chunk)

    assert updated.content == "updated"

    found = await repository.get_by_id(chunk.id)

    assert found is not None
    assert found.content == "updated"
