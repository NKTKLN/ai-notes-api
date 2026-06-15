"""Tests for message repository."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import ChatSession, Message, MessageRole, User
except ImportError:
    from ai_notes_api.db.models.chat_session import ChatSession
    from ai_notes_api.db.models.message import Message, MessageRole
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories import MessageListFilters
from ai_notes_api.repositories.message import MessageRepository


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
    """Persist a chat session for message repository tests.

    Args:
        async_session (AsyncSession): Database session used to persist the row.
        user_id (UUID): Identifier of the user who owns the chat session.
        title (str): Chat session title.

    Returns:
        ChatSession: Persisted chat session instance.
    """
    chat_session = ChatSession(
        user_id=user_id,
        title=title,
    )

    async_session.add(chat_session)
    await async_session.flush()
    await async_session.refresh(chat_session)

    return chat_session


def create_message(  # noqa: PLR0913
    *,
    session_id: UUID,
    content: str = "Test message",
    role: MessageRole = MessageRole.USER,
    provider: str | None = None,
    model_name: str | None = None,
    created_at: datetime | None = None,
) -> Message:
    """Create a message instance for repository tests.

    Args:
        session_id (UUID): Identifier of the chat session that owns the message.
        content (str): Message content.
        role (MessageRole): Message role.
        provider (str | None): Optional AI provider name.
        model_name (str | None): Optional AI model name.
        created_at (datetime | None): Optional explicit creation timestamp used to
            control message ordering in tests.

    Returns:
        Message: Message model instance.
    """
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        provider=provider,
        model_name=model_name,
    )

    if created_at is not None:
        message.created_at = created_at

    return message


@pytest.mark.asyncio
async def test_create_message_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful message creation."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    message = create_message(
        session_id=chat_session.id,
        content="Hello",
        role=MessageRole.USER,
    )

    created_message = await repository.create(message)

    assert created_message.id is not None
    assert created_message.session_id == chat_session.id
    assert created_message.content == "Hello"
    assert created_message.role == MessageRole.USER
    assert created_message.deleted_at is None


@pytest.mark.asyncio
async def test_get_by_id_message_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful message retrieval by identifier without user scope."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id, content="Hello")
    )

    message = await repository.get_by_id(created_message.id)

    assert message is not None
    assert message.id == created_message.id
    assert message.session_id == chat_session.id
    assert message.content == "Hello"
    assert message.deleted_at is None


@pytest.mark.asyncio
async def test_get_by_id_message_not_found(
    async_session: AsyncSession,
) -> None:
    """Test that message retrieval by identifier returns None when missing."""
    repository = MessageRepository(session=async_session)

    message = await repository.get_by_id(uuid4())

    assert message is None


@pytest.mark.asyncio
async def test_get_by_id_message_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that retrieval by identifier returns None for a soft-deleted message."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id)
    )

    await repository.soft_delete(created_message)

    message = await repository.get_by_id(created_message.id)

    assert message is None


@pytest.mark.asyncio
async def test_get_by_id_message_is_not_scoped_to_user(
    async_session: AsyncSession,
    other_user: User,
) -> None:
    """Test that retrieval by identifier is not restricted to a single owner."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=other_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id)
    )

    message = await repository.get_by_id(created_message.id)

    assert message is not None
    assert message.id == created_message.id


@pytest.mark.asyncio
async def test_get_message_for_user_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful message retrieval scoped to the owning user."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id, content="Hello")
    )

    message = await repository.get_by_id_for_user(test_user.id, created_message.id)

    assert message is not None
    assert message.id == created_message.id
    assert message.session_id == chat_session.id
    assert message.content == "Hello"


@pytest.mark.asyncio
async def test_get_message_for_user_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scoped message retrieval returns None when not found."""
    repository = MessageRepository(session=async_session)

    message = await repository.get_by_id_for_user(test_user.id, uuid4())

    assert message is None


@pytest.mark.asyncio
async def test_get_message_for_user_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that scoped retrieval returns None for a soft-deleted message."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id)
    )

    await repository.soft_delete(created_message)

    message = await repository.get_by_id_for_user(test_user.id, created_message.id)

    assert message is None


@pytest.mark.asyncio
async def test_get_message_for_user_other_user_cannot_access(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a message by identifier."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    created_message = await repository.create(
        create_message(session_id=chat_session.id)
    )

    message = await repository.get_by_id_for_user(other_user.id, created_message.id)

    assert message is None


@pytest.mark.asyncio
async def test_get_messages_list_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval ordered by creation date."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, content="First message")
    )
    await repository.create(
        create_message(session_id=chat_session.id, content="Second message")
    )

    filters = MessageListFilters(limit=10, offset=0)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 2
    assert messages[0].content == "Second message"
    assert messages[1].content == "First message"


@pytest.mark.asyncio
async def test_get_messages_list_empty_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful empty messages list retrieval."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    filters = MessageListFilters(limit=10, offset=0)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert messages == []


@pytest.mark.asyncio
async def test_get_messages_list_returns_only_user_owned_messages(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that messages list is scoped to the requested user."""
    repository = MessageRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned_message = await repository.create(
        create_message(session_id=owned_session.id, content="Owned message")
    )
    await repository.create(
        create_message(session_id=other_session.id, content="Other message")
    )

    filters = MessageListFilters(limit=10, offset=0)

    messages = await repository.get_list(test_user.id, owned_session.id, filters)

    assert len(messages) == 1
    assert messages[0].id == owned_message.id


@pytest.mark.asyncio
async def test_get_messages_list_returns_only_requested_session(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that messages list is scoped to the requested chat session."""
    repository = MessageRepository(session=async_session)
    first_session = await create_chat_session(async_session, user_id=test_user.id)
    second_session = await create_chat_session(async_session, user_id=test_user.id)

    first_message = await repository.create(
        create_message(session_id=first_session.id, content="First session message")
    )
    await repository.create(
        create_message(session_id=second_session.id, content="Second session message")
    )

    filters = MessageListFilters(limit=10, offset=0)

    messages = await repository.get_list(test_user.id, first_session.id, filters)

    assert len(messages) == 1
    assert messages[0].id == first_message.id


@pytest.mark.asyncio
async def test_get_messages_list_excludes_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that messages list excludes soft-deleted messages."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    active_message = await repository.create(
        create_message(session_id=chat_session.id, content="Active message")
    )
    deleted_message = await repository.create(
        create_message(session_id=chat_session.id, content="Deleted message")
    )

    await repository.soft_delete(deleted_message)

    filters = MessageListFilters(limit=10, offset=0)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].id == active_message.id


@pytest.mark.asyncio
async def test_get_messages_list_with_provider_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval filtered by provider."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, provider="anthropic")
    )
    await repository.create(
        create_message(session_id=chat_session.id, provider="openai")
    )

    filters = MessageListFilters(limit=10, offset=0, provider="anthropic")

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].provider == "anthropic"


@pytest.mark.asyncio
async def test_get_messages_list_with_model_name_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval filtered by model name."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, model_name="claude-opus-4-8")
    )
    await repository.create(
        create_message(session_id=chat_session.id, model_name="gpt-5")
    )

    filters = MessageListFilters(limit=10, offset=0, model_name="claude-opus-4-8")

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].model_name == "claude-opus-4-8"


@pytest.mark.asyncio
async def test_get_messages_list_with_role_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval filtered by role."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, role=MessageRole.USER)
    )
    await repository.create(
        create_message(session_id=chat_session.id, role=MessageRole.ASSISTANT)
    )

    filters = MessageListFilters(limit=10, offset=0, role=MessageRole.ASSISTANT)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].role == MessageRole.ASSISTANT


@pytest.mark.asyncio
async def test_get_messages_list_with_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval filtered by content search."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, content="FastAPI is great")
    )
    await repository.create(
        create_message(session_id=chat_session.id, content="Django is great")
    )

    filters = MessageListFilters(limit=10, offset=0, search="fastapi")

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].content == "FastAPI is great"


@pytest.mark.asyncio
async def test_get_messages_list_with_search_whitespace_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with whitespace around search query."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, content="FastAPI is great")
    )
    await repository.create(
        create_message(session_id=chat_session.id, content="Django is great")
    )

    filters = MessageListFilters(limit=10, offset=0, search="   fastapi   ")

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 1
    assert messages[0].content == "FastAPI is great"


@pytest.mark.asyncio
async def test_get_messages_list_with_empty_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful list retrieval with empty search query."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(
        create_message(session_id=chat_session.id, content="First message")
    )
    await repository.create(
        create_message(session_id=chat_session.id, content="Second message")
    )

    filters = MessageListFilters(limit=10, offset=0, search="")

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 2


@pytest.mark.asyncio
async def test_get_messages_list_filters_do_not_leak_other_user_messages(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that filters are applied only inside the requested user's messages."""
    repository = MessageRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned_message = await repository.create(
        create_message(session_id=owned_session.id, content="Matching owned message")
    )
    await repository.create(
        create_message(session_id=other_session.id, content="Matching other message")
    )

    filters = MessageListFilters(limit=10, offset=0, search="matching")

    messages = await repository.get_list(test_user.id, owned_session.id, filters)

    assert len(messages) == 1
    assert messages[0].id == owned_message.id


@pytest.mark.asyncio
async def test_get_messages_list_with_limit_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval with limit."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    await repository.create(create_message(session_id=chat_session.id, content="First"))
    await repository.create(
        create_message(session_id=chat_session.id, content="Second")
    )
    await repository.create(create_message(session_id=chat_session.id, content="Third"))

    filters = MessageListFilters(limit=2, offset=0)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 2


@pytest.mark.asyncio
async def test_get_messages_list_with_offset_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful messages list retrieval with offset."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    first_message = await repository.create(
        create_message(session_id=chat_session.id, content="First")
    )
    second_message = await repository.create(
        create_message(session_id=chat_session.id, content="Second")
    )
    third_message = await repository.create(
        create_message(session_id=chat_session.id, content="Third")
    )

    filters = MessageListFilters(limit=10, offset=1)

    messages = await repository.get_list(test_user.id, chat_session.id, filters)

    assert len(messages) == 2
    assert messages[0].id == second_message.id
    assert messages[1].id == first_message.id
    assert third_message.id not in [message.id for message in messages]


@pytest.mark.asyncio
async def test_get_last_messages_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful latest messages retrieval ordered by creation date."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    await repository.create(
        create_message(
            session_id=chat_session.id,
            content="First message",
            created_at=base,
        )
    )
    await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Second message",
            created_at=base + timedelta(seconds=1),
        )
    )

    messages = await repository.get_last_messages(
        test_user.id, chat_session.id, limit=10
    )

    assert len(messages) == 2
    assert messages[0].content == "Second message"
    assert messages[1].content == "First message"


@pytest.mark.asyncio
async def test_get_last_messages_empty_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful empty latest messages retrieval."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    messages = await repository.get_last_messages(
        test_user.id, chat_session.id, limit=10
    )

    assert messages == []


@pytest.mark.asyncio
async def test_get_last_messages_respects_limit(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that latest messages retrieval returns only the most recent ones."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    await repository.create(
        create_message(
            session_id=chat_session.id,
            content="First",
            created_at=base,
        )
    )
    await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Second",
            created_at=base + timedelta(seconds=1),
        )
    )
    await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Third",
            created_at=base + timedelta(seconds=2),
        )
    )

    messages = await repository.get_last_messages(
        test_user.id, chat_session.id, limit=2
    )

    assert len(messages) == 2
    assert messages[0].content == "Third"
    assert messages[1].content == "Second"


@pytest.mark.asyncio
async def test_get_last_messages_excludes_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that latest messages retrieval excludes soft-deleted messages."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    active_message = await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Active message",
            created_at=base,
        )
    )
    deleted_message = create_message(
        session_id=chat_session.id,
        content="Deleted message",
        created_at=base + timedelta(seconds=1),
    )
    deleted_message.deleted_at = base + timedelta(seconds=2)
    await repository.create(deleted_message)

    messages = await repository.get_last_messages(
        test_user.id, chat_session.id, limit=10
    )

    assert len(messages) == 1
    assert messages[0].id == active_message.id


@pytest.mark.asyncio
async def test_get_last_messages_returns_only_user_owned_messages(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that latest messages retrieval is scoped to the requested user."""
    repository = MessageRepository(session=async_session)
    owned_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=other_user.id)

    owned_message = await repository.create(
        create_message(session_id=owned_session.id, content="Owned message")
    )
    await repository.create(
        create_message(session_id=other_session.id, content="Other message")
    )

    messages = await repository.get_last_messages(
        test_user.id, owned_session.id, limit=10
    )

    assert len(messages) == 1
    assert messages[0].id == owned_message.id


@pytest.mark.asyncio
async def test_get_last_messages_returns_only_requested_session(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that latest messages retrieval is scoped to the requested session."""
    repository = MessageRepository(session=async_session)
    first_session = await create_chat_session(async_session, user_id=test_user.id)
    second_session = await create_chat_session(async_session, user_id=test_user.id)

    first_message = await repository.create(
        create_message(session_id=first_session.id, content="First session message")
    )
    await repository.create(
        create_message(session_id=second_session.id, content="Second session message")
    )

    messages = await repository.get_last_messages(
        test_user.id, first_session.id, limit=10
    )

    assert len(messages) == 1
    assert messages[0].id == first_message.id


@pytest.mark.asyncio
async def test_update_message_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful message update."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    message = await repository.create(
        create_message(session_id=chat_session.id, content="Old content")
    )

    message.content = "New content"

    updated_message = await repository.update(message)

    assert updated_message.id == message.id
    assert updated_message.content == "New content"

    found_message = await repository.get_by_id(message.id)

    assert found_message is not None
    assert found_message.content == "New content"


@pytest.mark.asyncio
async def test_delete_message_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful message soft deletion."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    message = await repository.create(create_message(session_id=chat_session.id))

    await repository.soft_delete(message)

    assert message.deleted_at is not None
    assert isinstance(message.deleted_at, datetime)


@pytest.mark.asyncio
async def test_delete_message_hides_message_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion hides the message from repository reads."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    message = await repository.create(create_message(session_id=chat_session.id))

    await repository.soft_delete(message)

    found_message = await repository.get_by_id(message.id)

    assert found_message is None


@pytest.mark.asyncio
async def test_delete_message_preserves_database_row_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion preserves the database row."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    message = await repository.create(create_message(session_id=chat_session.id))

    await repository.soft_delete(message)

    result = await async_session.execute(
        select(Message).where(Message.id == message.id)
    )
    stored_message = result.scalar_one_or_none()

    assert stored_message is not None
    assert stored_message.id == message.id
    assert stored_message.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_message_cascades_to_following_messages_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion also removes later messages in the same session."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    earlier_message = await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Earlier message",
            created_at=base,
        )
    )
    target_message = await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Target message",
            created_at=base + timedelta(seconds=1),
        )
    )
    later_message = await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Later message",
            created_at=base + timedelta(seconds=2),
        )
    )

    await repository.soft_delete(target_message)

    assert await repository.get_by_id(earlier_message.id) is not None
    assert await repository.get_by_id(target_message.id) is None
    assert await repository.get_by_id(later_message.id) is None


@pytest.mark.asyncio
async def test_delete_message_does_not_affect_other_sessions_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that cascading soft deletion is scoped to the message's session."""
    repository = MessageRepository(session=async_session)
    target_session = await create_chat_session(async_session, user_id=test_user.id)
    other_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)

    target_message = await repository.create(
        create_message(
            session_id=target_session.id,
            content="Target message",
            created_at=base,
        )
    )
    other_message = await repository.create(
        create_message(
            session_id=other_session.id,
            content="Later message in another session",
            created_at=base + timedelta(seconds=1),
        )
    )

    await repository.soft_delete(target_message)

    assert await repository.get_by_id(target_message.id) is None
    assert await repository.get_by_id(other_message.id) is not None


@pytest.mark.asyncio
async def test_delete_message_keeps_already_deleted_timestamp_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that cascading deletion does not overwrite already-deleted messages."""
    repository = MessageRepository(session=async_session)
    chat_session = await create_chat_session(async_session, user_id=test_user.id)

    base = datetime.now(UTC)
    already_deleted_at = base + timedelta(seconds=5)

    target_message = await repository.create(
        create_message(
            session_id=chat_session.id,
            content="Target message",
            created_at=base,
        )
    )
    later_deleted = create_message(
        session_id=chat_session.id,
        content="Already deleted later message",
        created_at=base + timedelta(seconds=1),
    )
    later_deleted.deleted_at = already_deleted_at
    later_deleted = await repository.create(later_deleted)

    await repository.soft_delete(target_message)

    result = await async_session.execute(
        select(Message).where(Message.id == later_deleted.id)
    )
    stored_message = result.scalar_one()

    assert stored_message.deleted_at == already_deleted_at
