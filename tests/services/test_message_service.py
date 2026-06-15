"""Tests for message service."""

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import ChatSession, Message, MessageRole
from ai_notes_api.exceptions import ChatSessionNotFoundError, MessageNotFoundError
from ai_notes_api.repositories import MessageListFilters
from ai_notes_api.repositories.chat_session import ChatSessionRepository
from ai_notes_api.repositories.message import MessageRepository
from ai_notes_api.schemas import (
    AssistantMessageCreateSchema,
    MessageListQuerySchema,
    UserMessageCreateSchema,
)
from ai_notes_api.services.message import MessageService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_MESSAGE_ID_2 = UUID("55555555-5555-5555-5555-555555555555")


class FakeChatSessionRepository:
    """Fake chat session repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.chat_sessions: dict[UUID, ChatSession] = {}

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> ChatSession | None:
        """Return chat session by id."""
        chat_session = self.chat_sessions.get(session_id)

        if (
            chat_session is not None
            and chat_session.user_id == user_id
            and chat_session.deleted_at is None
        ):
            return chat_session

        return None


class FakeMessageRepository:
    """Fake message repository used for testing service behavior."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.messages: dict[UUID, Message] = {}
        self.created_message: Message | None = None
        self._sessions = FakeChatSessionRepository()

    async def create(self, message: Message) -> Message:
        """Create message."""
        message.id = TEST_MESSAGE_ID
        self.created_message = message
        self.messages[message.id] = message
        return message

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        message_id: UUID,
    ) -> Message | None:
        """Return message by id for the owning user."""
        message = self.messages.get(message_id)

        if message is None or message.deleted_at is not None:
            return None

        session = self._sessions.chat_sessions.get(message.session_id)

        if session is None or session.user_id != user_id:
            return None

        return message

    def _owned_messages(self, user_id: UUID, session_id: UUID) -> list[Message]:
        """Return non-deleted messages from a session owned by the user."""
        session = self._sessions.chat_sessions.get(session_id)

        if session is None or session.user_id != user_id:
            return []

        return [
            message
            for message in self.messages.values()
            if message.session_id == session_id and message.deleted_at is None
        ]

    async def get_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: MessageListFilters,
    ) -> list[Message]:
        """Return filtered messages ordered from newest to oldest."""
        messages = self._owned_messages(user_id, session_id)

        if filters.role is not None:
            messages = [m for m in messages if m.role == filters.role]

        if filters.provider is not None:
            messages = [m for m in messages if m.provider == filters.provider]

        if filters.model_name is not None:
            messages = [m for m in messages if m.model_name == filters.model_name]

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                messages = [m for m in messages if search in m.content]

        messages.sort(key=lambda m: m.created_at, reverse=True)

        return messages[filters.offset : filters.offset + filters.limit]

    async def get_last_messages(
        self,
        user_id: UUID,
        session_id: UUID,
        limit: int,
    ) -> list[Message]:
        """Return latest messages ordered from newest to oldest."""
        messages = self._owned_messages(user_id, session_id)

        messages.sort(key=lambda m: m.created_at, reverse=True)

        return messages[:limit]

    async def soft_delete(self, message: Message) -> None:
        """Soft-delete message."""
        stored = self.messages.get(message.id)

        if stored is not None:
            stored.deleted_at = datetime.now(UTC)


def _build_service() -> tuple[
    FakeMessageRepository,
    FakeChatSessionRepository,
    MessageService,
]:
    """Build a message service wired with fake repositories."""
    message_repository = FakeMessageRepository()
    session_repository = FakeChatSessionRepository()
    message_repository._sessions = session_repository

    service = MessageService(
        message_repository=cast(MessageRepository, message_repository),
        session_repository=cast(ChatSessionRepository, session_repository),
    )

    return message_repository, session_repository, service


def _add_session(
    session_repository: FakeChatSessionRepository,
    user_id: UUID = TEST_USER_ID,
    session_id: UUID = TEST_SESSION_ID,
) -> None:
    """Register an owned chat session in the fake repository."""
    session_repository.chat_sessions[session_id] = ChatSession(
        id=session_id,
        user_id=user_id,
        title="Test session",
    )


@pytest.mark.asyncio
async def test_create_user_message_success() -> None:
    """Test successful user message creation."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    data = UserMessageCreateSchema(session_id=TEST_SESSION_ID, content="Hello")

    message = await service.create_user_message(TEST_USER_ID, data)

    assert message.session_id == TEST_SESSION_ID
    assert message.content == "Hello"
    assert message.role == MessageRole.USER
    assert message_repository.created_message is message


@pytest.mark.asyncio
async def test_create_user_message_session_not_found() -> None:
    """Test that user message creation fails without an accessible session."""
    _, _, service = _build_service()

    data = UserMessageCreateSchema(session_id=TEST_SESSION_ID, content="Hello")

    with pytest.raises(ChatSessionNotFoundError):
        await service.create_user_message(TEST_USER_ID, data)


@pytest.mark.asyncio
async def test_create_user_message_session_owned_by_another_user() -> None:
    """Test that a user cannot create a message in another user's session."""
    _, session_repository, service = _build_service()
    _add_session(session_repository, user_id=TEST_USER_ID)

    data = UserMessageCreateSchema(session_id=TEST_SESSION_ID, content="Hello")

    with pytest.raises(ChatSessionNotFoundError):
        await service.create_user_message(TEST_USER_ID_2, data)


@pytest.mark.asyncio
async def test_create_assistant_message_success() -> None:
    """Test successful assistant message creation with metadata."""
    _, session_repository, service = _build_service()
    _add_session(session_repository)

    data = AssistantMessageCreateSchema(
        session_id=TEST_SESSION_ID,
        content="Hi there",
        provider="openai",
        model_name="gpt-4",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )

    message = await service.create_assistant_message(TEST_USER_ID, data)

    assert message.role == MessageRole.ASSISTANT
    assert message.content == "Hi there"
    assert message.provider == "openai"
    assert message.model_name == "gpt-4"
    assert message.prompt_tokens == 10
    assert message.completion_tokens == 20
    assert message.total_tokens == 30


@pytest.mark.asyncio
async def test_create_assistant_message_session_not_found() -> None:
    """Test that assistant message creation fails without an accessible session."""
    _, _, service = _build_service()

    data = AssistantMessageCreateSchema(session_id=TEST_SESSION_ID, content="Hi")

    with pytest.raises(ChatSessionNotFoundError):
        await service.create_assistant_message(TEST_USER_ID, data)


@pytest.mark.asyncio
async def test_get_messages_list_success() -> None:
    """Test successful message list retrieval with filters."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    base_time = datetime(2026, 6, 16, tzinfo=UTC)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Question about Python",
        role=MessageRole.USER,
        created_at=base_time,
    )
    message_repository.messages[TEST_MESSAGE_ID_2] = Message(
        id=TEST_MESSAGE_ID_2,
        session_id=TEST_SESSION_ID,
        content="Answer about Go",
        role=MessageRole.ASSISTANT,
        created_at=base_time + timedelta(minutes=1),
    )

    filters = MessageListQuerySchema(role=MessageRole.USER)

    messages = await service.get_messages_list(TEST_USER_ID, TEST_SESSION_ID, filters)

    assert len(messages) == 1
    assert messages[0].id == TEST_MESSAGE_ID


@pytest.mark.asyncio
async def test_get_messages_list_session_not_found() -> None:
    """Test that listing messages fails without an accessible session."""
    _, _, service = _build_service()

    filters = MessageListQuerySchema()

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_messages_list(TEST_USER_ID, TEST_SESSION_ID, filters)


@pytest.mark.asyncio
async def test_get_message_success() -> None:
    """Test successful message retrieval by identifier."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Hello",
        role=MessageRole.USER,
    )

    message = await service.get_message(TEST_USER_ID, TEST_MESSAGE_ID)

    assert message.id == TEST_MESSAGE_ID
    assert message.content == "Hello"


@pytest.mark.asyncio
async def test_get_message_not_found_by_id() -> None:
    """Test that retrieval raises an error when message is not found."""
    _, _, service = _build_service()

    with pytest.raises(MessageNotFoundError):
        await service.get_message(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_get_message_not_found_for_another_user() -> None:
    """Test that another user's message cannot be retrieved."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository, user_id=TEST_USER_ID)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Hello",
        role=MessageRole.USER,
    )

    with pytest.raises(MessageNotFoundError):
        await service.get_message(TEST_USER_ID_2, TEST_MESSAGE_ID)


@pytest.mark.asyncio
async def test_get_context_messages_returns_chronological_order() -> None:
    """Test that context messages are returned from oldest to newest."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    base_time = datetime(2026, 6, 16, tzinfo=UTC)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Oldest",
        role=MessageRole.USER,
        created_at=base_time,
    )
    message_repository.messages[TEST_MESSAGE_ID_2] = Message(
        id=TEST_MESSAGE_ID_2,
        session_id=TEST_SESSION_ID,
        content="Newest",
        role=MessageRole.ASSISTANT,
        created_at=base_time + timedelta(minutes=1),
    )

    messages = await service.get_context_messages(TEST_USER_ID, TEST_SESSION_ID)

    assert [message.content for message in messages] == ["Oldest", "Newest"]


@pytest.mark.asyncio
async def test_get_context_messages_respects_limit() -> None:
    """Test that context messages keep only the most recent within the limit."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    base_time = datetime(2026, 6, 16, tzinfo=UTC)

    for index in range(5):
        message_id = uuid4()
        message_repository.messages[message_id] = Message(
            id=message_id,
            session_id=TEST_SESSION_ID,
            content=f"Message {index}",
            role=MessageRole.USER,
            created_at=base_time + timedelta(minutes=index),
        )

    messages = await service.get_context_messages(
        TEST_USER_ID, TEST_SESSION_ID, limit=2
    )

    assert [message.content for message in messages] == ["Message 3", "Message 4"]


@pytest.mark.asyncio
async def test_get_context_messages_session_not_found() -> None:
    """Test that fetching context fails without an accessible session."""
    _, _, service = _build_service()

    with pytest.raises(ChatSessionNotFoundError):
        await service.get_context_messages(TEST_USER_ID, TEST_SESSION_ID)


@pytest.mark.asyncio
async def test_delete_message_success() -> None:
    """Test successful message deletion."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Hello",
        role=MessageRole.USER,
    )

    await service.delete_message(TEST_USER_ID, TEST_MESSAGE_ID)

    assert message_repository.messages[TEST_MESSAGE_ID].deleted_at is not None


@pytest.mark.asyncio
async def test_delete_message_not_found_by_id() -> None:
    """Test that delete raises an error when message is not found."""
    _, _, service = _build_service()

    with pytest.raises(MessageNotFoundError):
        await service.delete_message(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_delete_message_not_found_for_another_user() -> None:
    """Test that another user's message cannot be deleted."""
    message_repository, session_repository, service = _build_service()
    _add_session(session_repository, user_id=TEST_USER_ID)

    message_repository.messages[TEST_MESSAGE_ID] = Message(
        id=TEST_MESSAGE_ID,
        session_id=TEST_SESSION_ID,
        content="Hello",
        role=MessageRole.USER,
    )

    with pytest.raises(MessageNotFoundError):
        await service.delete_message(TEST_USER_ID_2, TEST_MESSAGE_ID)

    assert message_repository.messages[TEST_MESSAGE_ID].deleted_at is None
