"""Tests for document repository."""

from datetime import UTC, datetime, timedelta
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
from ai_notes_api.repositories.document import DocumentRepository


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
    title: str = "Test chat session",
) -> ChatSession:
    """Persist a chat session for document repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the chat session.
        title (str): Chat session title.

    Returns:
        ChatSession: Persisted chat session instance.
    """
    chat_session = ChatSession(user_id=user_id, title=title)

    async_session.add(chat_session)
    await async_session.flush()
    await async_session.refresh(chat_session)

    return chat_session


def create_document(
    *,
    user_id: UUID,
    session_id: UUID,
    filename: str = "test.pdf",
    status: DocumentStatus = DocumentStatus.UPLOADED,
    created_at: datetime | None = None,
) -> Document:
    """Create a document instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the document.
        session_id (UUID): Identifier of the chat session that owns the document.
        filename (str): Original document file name.
        status (DocumentStatus): Document processing status.
        created_at (datetime | None): Optional explicit creation timestamp used to
            control document ordering in tests.

    Returns:
        Document: Document model instance.
    """
    document = Document(
        user_id=user_id,
        session_id=session_id,
        filename=filename,
        content_type="application/pdf",
        file_size=1024,
        checksum_sha256="checksum",
        storage_bucket="documents",
        storage_object_name="object",
        status=status,
    )

    if created_at is not None:
        document.created_at = created_at

    return document


@pytest.mark.asyncio
async def test_create_document_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document creation."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    document = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    assert document.id is not None
    assert document.user_id == test_user.id
    assert document.session_id == chat_session.id
    assert document.status == DocumentStatus.UPLOADED


@pytest.mark.asyncio
async def test_get_by_id_document_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document retrieval by identifier."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    document = await repository.get_by_id(created.id)

    assert document is not None
    assert document.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_document_not_found(async_session: AsyncSession) -> None:
    """Test that document retrieval by identifier returns None when missing."""
    repository = DocumentRepository(session=async_session)

    document = await repository.get_by_id(uuid4())

    assert document is None


@pytest.mark.asyncio
async def test_get_by_id_document_excludes_soft_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that document retrieval by identifier ignores soft-deleted rows."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )
    await repository.soft_delete(created)

    document = await repository.get_by_id(created.id)

    assert document is None


@pytest.mark.asyncio
async def test_get_by_id_for_user_document_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document retrieval scoped to the owning user."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    document = await repository.get_by_id_for_user(test_user.id, created.id)

    assert document is not None
    assert document.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_for_user_document_other_user_cannot_access(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a document by identifier."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    document = await repository.get_by_id_for_user(other_user.id, created.id)

    assert document is None


@pytest.mark.asyncio
async def test_get_list_for_session_orders_by_created_at_desc(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that documents list is ordered by creation date in descending order."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    await repository.create(
        create_document(
            user_id=test_user.id,
            session_id=chat_session.id,
            filename="first.pdf",
            created_at=base,
        )
    )
    await repository.create(
        create_document(
            user_id=test_user.id,
            session_id=chat_session.id,
            filename="second.pdf",
            created_at=base + timedelta(seconds=1),
        )
    )

    documents = await repository.get_list_for_session(test_user.id, chat_session.id)

    assert [document.filename for document in documents] == [
        "second.pdf",
        "first.pdf",
    ]


@pytest.mark.asyncio
async def test_get_list_for_session_scoped_to_user_and_session(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that documents list is scoped to the requested user and session."""
    repository = DocumentRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned = await repository.create(
        create_document(user_id=test_user.id, session_id=owned_session.id)
    )
    await repository.create(
        create_document(user_id=other_user.id, session_id=other_session.id)
    )

    documents = await repository.get_list_for_session(test_user.id, owned_session.id)

    assert len(documents) == 1
    assert documents[0].id == owned.id


@pytest.mark.asyncio
async def test_get_list_for_session_excludes_soft_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that documents list ignores soft-deleted rows."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    kept = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )
    deleted = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )
    await repository.soft_delete(deleted)

    documents = await repository.get_list_for_session(test_user.id, chat_session.id)

    assert len(documents) == 1
    assert documents[0].id == kept.id


@pytest.mark.asyncio
async def test_update_document_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful document update."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    document = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    document.status = DocumentStatus.READY

    updated = await repository.update(document)

    assert updated.status == DocumentStatus.READY

    found = await repository.get_by_id(document.id)

    assert found is not None
    assert found.status == DocumentStatus.READY


@pytest.mark.asyncio
async def test_soft_delete_document_cascades_to_chunks(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft-deleting a document also soft-deletes its chunks."""
    repository = DocumentRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    document = await repository.create(
        create_document(user_id=test_user.id, session_id=chat_session.id)
    )

    chunk = DocumentChunk(
        user_id=test_user.id,
        session_id=chat_session.id,
        document_id=document.id,
        chunk_index=0,
        content="chunk",
        content_hash="hash",
        embedding=[0.0] * 1536,
        embedding_model="text-embedding-3-small",
    )
    async_session.add(chunk)
    await async_session.flush()

    await repository.soft_delete(document)

    await async_session.refresh(document)
    await async_session.refresh(chunk)

    assert document.deleted_at is not None
    assert chunk.deleted_at is not None
