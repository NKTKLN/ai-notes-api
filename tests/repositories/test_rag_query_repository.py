"""Tests for RAG query repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import ChatSession, RagQuery, RagQueryStatus, User
from ai_notes_api.repositories.rag_query import RagQueryRepository


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
    """Persist a chat session for RAG query repository tests.

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


def create_rag_query(  # noqa: PLR0913
    *,
    user_id: UUID,
    session_id: UUID,
    question: str = "What is RAG?",
    top_k: int = 5,
    status: RagQueryStatus = RagQueryStatus.QUEUED,
    created_at: datetime | None = None,
) -> RagQuery:
    """Create a RAG query instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the RAG query.
        session_id (UUID): Identifier of the chat session that owns the RAG query.
        question (str): User question.
        top_k (int): Number of chunks to retrieve.
        status (RagQueryStatus): RAG query status.
        created_at (datetime | None): Optional explicit creation timestamp used to
            control RAG query ordering in tests.

    Returns:
        RagQuery: RAG query model instance.
    """
    rag_query = RagQuery(
        user_id=user_id,
        session_id=session_id,
        question=question,
        top_k=top_k,
        status=status,
    )

    if created_at is not None:
        rag_query.created_at = created_at

    return rag_query


@pytest.mark.asyncio
async def test_create_rag_query_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful RAG query creation."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    rag_query = await repository.create(
        create_rag_query(user_id=test_user.id, session_id=chat_session.id)
    )

    assert rag_query.id is not None
    assert rag_query.user_id == test_user.id
    assert rag_query.session_id == chat_session.id
    assert rag_query.status == RagQueryStatus.QUEUED


@pytest.mark.asyncio
async def test_get_by_id_rag_query_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful RAG query retrieval by identifier."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_rag_query(user_id=test_user.id, session_id=chat_session.id)
    )

    rag_query = await repository.get_by_id(created.id)

    assert rag_query is not None
    assert rag_query.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_rag_query_not_found(async_session: AsyncSession) -> None:
    """Test that RAG query retrieval by identifier returns None when missing."""
    repository = RagQueryRepository(session=async_session)

    rag_query = await repository.get_by_id(uuid4())

    assert rag_query is None


@pytest.mark.asyncio
async def test_get_by_id_for_user_rag_query_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful RAG query retrieval scoped to the owning user."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_rag_query(user_id=test_user.id, session_id=chat_session.id)
    )

    rag_query = await repository.get_by_id_for_user(test_user.id, created.id)

    assert rag_query is not None
    assert rag_query.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_for_user_rag_query_other_user_cannot_access(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a RAG query by identifier."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created = await repository.create(
        create_rag_query(user_id=test_user.id, session_id=chat_session.id)
    )

    rag_query = await repository.get_by_id_for_user(other_user.id, created.id)

    assert rag_query is None


@pytest.mark.asyncio
async def test_get_list_for_session_orders_by_created_at_desc(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that RAG queries list is ordered by creation date in descending order."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    await repository.create(
        create_rag_query(
            user_id=test_user.id,
            session_id=chat_session.id,
            question="First",
            created_at=base,
        )
    )
    await repository.create(
        create_rag_query(
            user_id=test_user.id,
            session_id=chat_session.id,
            question="Second",
            created_at=base + timedelta(seconds=1),
        )
    )

    rag_queries = await repository.get_list_for_session(test_user.id, chat_session.id)

    assert [rag_query.question for rag_query in rag_queries] == ["Second", "First"]


@pytest.mark.asyncio
async def test_get_list_for_session_scoped_to_user_and_session(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that RAG queries list is scoped to the requested user and session."""
    repository = RagQueryRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned = await repository.create(
        create_rag_query(user_id=test_user.id, session_id=owned_session.id)
    )
    await repository.create(
        create_rag_query(user_id=other_user.id, session_id=other_session.id)
    )

    rag_queries = await repository.get_list_for_session(test_user.id, owned_session.id)

    assert len(rag_queries) == 1
    assert rag_queries[0].id == owned.id


@pytest.mark.asyncio
async def test_update_rag_query_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful RAG query update."""
    repository = RagQueryRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    rag_query = await repository.create(
        create_rag_query(
            user_id=test_user.id,
            session_id=chat_session.id,
            status=RagQueryStatus.QUEUED,
        )
    )

    rag_query.status = RagQueryStatus.COMPLETED
    rag_query.answer = "RAG is retrieval-augmented generation."

    updated = await repository.update(rag_query)

    assert updated.status == RagQueryStatus.COMPLETED
    assert updated.answer == "RAG is retrieval-augmented generation."

    found = await repository.get_by_id(rag_query.id)

    assert found is not None
    assert found.status == RagQueryStatus.COMPLETED
