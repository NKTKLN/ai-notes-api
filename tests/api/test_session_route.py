"""Tests for chat session API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.chat_sessions import router
from ai_notes_api.api.v1.dependencies import (
    get_chat_session_service,
    get_current_user,
    get_message_service,
)
from ai_notes_api.db.models import MessageRole, User
from ai_notes_api.schemas import ChatSessionResponseSchema, MessageResponseSchema

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_SESSION_ID_2 = UUID("33333333-3333-3333-3333-333333333333")
TEST_MESSAGE_ID = UUID("44444444-4444-4444-4444-444444444444")
TEST_MESSAGE_ID_2 = UUID("55555555-5555-5555-5555-555555555555")


def create_test_user() -> User:
    """Create current user for router tests.

    Returns:
        User: Test user model instance.
    """
    return User(
        id=TEST_USER_ID,
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )


def create_chat_session_response(
    *,
    session_id: UUID = TEST_SESSION_ID,
    title: str = "Test chat session",
) -> ChatSessionResponseSchema:
    """Create chat session response schema for router tests.

    Args:
        session_id (UUID): Unique chat session identifier.
        title (str): Chat session title.

    Returns:
        ChatSessionResponseSchema: Chat session response schema instance.
    """
    now = datetime.now(UTC)

    return ChatSessionResponseSchema(
        id=session_id,
        title=title,
        created_at=now,
        updated_at=now,
    )


def create_message_response(
    *,
    message_id: UUID = TEST_MESSAGE_ID,
    role: MessageRole = MessageRole.USER,
    content: str = "Test message",
) -> MessageResponseSchema:
    """Create message response schema for router tests.

    Args:
        message_id (UUID): Unique message identifier.
        role (MessageRole): Message role.
        content (str): Message content.

    Returns:
        MessageResponseSchema: Message response schema instance.
    """
    return MessageResponseSchema(
        id=message_id,
        session_id=TEST_SESSION_ID,
        role=role,
        content=content,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def chat_session_service_mock() -> AsyncMock:
    """Create mocked chat session service.

    Returns:
        AsyncMock: Mocked chat session service dependency.
    """
    return AsyncMock()


@pytest.fixture
def message_service_mock() -> AsyncMock:
    """Create mocked message service.

    Returns:
        AsyncMock: Mocked message service dependency.
    """
    return AsyncMock()


@pytest.fixture
def client(
    chat_session_service_mock: AsyncMock,
    message_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        chat_session_service_mock (AsyncMock): Mocked chat session service dependency.
        message_service_mock (AsyncMock): Mocked message service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_chat_session_service] = lambda: (
        chat_session_service_mock
    )
    app.dependency_overrides[get_message_service] = lambda: message_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_create_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session creation."""
    chat_session_service_mock.create_chat_session.return_value = (
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="Test session",
        )
    )

    response = client.post(
        "/chat/sessions",
        json={
            "title": "Test session",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(TEST_SESSION_ID)
    assert data["title"] == "Test session"

    chat_session_service_mock.create_chat_session.assert_awaited_once()

    user_id, create_data = chat_session_service_mock.create_chat_session.await_args.args

    assert user_id == TEST_USER_ID
    assert create_data.title == "Test session"


def test_get_chat_sessions_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat sessions list retrieval."""
    chat_session_service_mock.get_chat_sessions_list.return_value = [
        create_chat_session_response(
            session_id=TEST_SESSION_ID_2,
            title="Second session",
        ),
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="First session",
        ),
    ]

    response = client.get("/chat/sessions?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 2
    assert len(data["items"]) == 2

    assert data["items"][0]["id"] == str(TEST_SESSION_ID_2)
    assert data["items"][0]["title"] == "Second session"

    assert data["items"][1]["id"] == str(TEST_SESSION_ID)
    assert data["items"][1]["title"] == "First session"

    chat_session_service_mock.get_chat_sessions_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_chat_sessions_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_chat_sessions_empty_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful empty chat sessions list retrieval."""
    chat_session_service_mock.get_chat_sessions_list.return_value = []

    response = client.get("/chat/sessions?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 0

    chat_session_service_mock.get_chat_sessions_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_chat_sessions_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_chat_sessions_with_filters_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat sessions list retrieval with filters."""
    chat_session_service_mock.get_chat_sessions_list.return_value = [
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="Matching session",
        )
    ]

    response = client.get(
        "/chat/sessions",
        params={
            "search": "matching",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["id"] == str(TEST_SESSION_ID)
    assert item["title"] == "Matching session"

    chat_session_service_mock.get_chat_sessions_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_chat_sessions_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.search == "matching"
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session retrieval by identifier."""
    chat_session_service_mock.get_chat_session.return_value = (
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="Test session",
        )
    )

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_SESSION_ID)
    assert data["title"] == "Test session"

    chat_session_service_mock.get_chat_session.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_update_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session update."""
    chat_session_service_mock.update_chat_session.return_value = (
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="Updated session",
        )
    )

    response = client.patch(
        f"/chat/sessions/{TEST_SESSION_ID}",
        json={
            "title": "Updated session",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_SESSION_ID)
    assert data["title"] == "Updated session"

    chat_session_service_mock.update_chat_session.assert_awaited_once()

    user_id, session_id, update_data = (
        chat_session_service_mock.update_chat_session.await_args.args
    )

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID
    assert update_data.title == "Updated session"


def test_delete_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session deletion."""
    chat_session_service_mock.delete_chat_session.return_value = None

    response = client.delete(f"/chat/sessions/{TEST_SESSION_ID}")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    chat_session_service_mock.delete_chat_session.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_create_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session creation passes current user id to service."""
    chat_session_service_mock.create_chat_session.return_value = (
        create_chat_session_response(session_id=TEST_SESSION_ID)
    )

    response = client.post(
        "/chat/sessions",
        json={
            "title": "Test chat session",
        },
    )

    assert response.status_code == 201

    chat_session_service_mock.create_chat_session.assert_awaited_once()

    user_id, _ = chat_session_service_mock.create_chat_session.await_args.args

    assert user_id == TEST_USER_ID


def test_get_chat_sessions_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat sessions list retrieval passes current user id to service."""
    chat_session_service_mock.get_chat_sessions_list.return_value = []

    response = client.get("/chat/sessions")

    assert response.status_code == 200

    chat_session_service_mock.get_chat_sessions_list.assert_awaited_once()

    user_id, _ = chat_session_service_mock.get_chat_sessions_list.await_args.args

    assert user_id == TEST_USER_ID


def test_get_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session retrieval passes current user id to service."""
    chat_session_service_mock.get_chat_session.return_value = (
        create_chat_session_response(session_id=TEST_SESSION_ID)
    )

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}")

    assert response.status_code == 200

    chat_session_service_mock.get_chat_session.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_update_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session update passes current user id to service."""
    chat_session_service_mock.update_chat_session.return_value = (
        create_chat_session_response(
            session_id=TEST_SESSION_ID,
            title="Updated session",
        )
    )

    response = client.patch(
        f"/chat/sessions/{TEST_SESSION_ID}",
        json={
            "title": "Updated session",
        },
    )

    assert response.status_code == 200

    chat_session_service_mock.update_chat_session.assert_awaited_once()

    user_id, session_id, _ = (
        chat_session_service_mock.update_chat_session.await_args.args
    )

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID


def test_delete_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session deletion passes current user id to service."""
    chat_session_service_mock.delete_chat_session.return_value = None

    response = client.delete(f"/chat/sessions/{TEST_SESSION_ID}")

    assert response.status_code == 200

    chat_session_service_mock.delete_chat_session.assert_awaited_once_with(
        TEST_USER_ID, TEST_SESSION_ID
    )


def test_get_chat_session_messages_success(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test successful chat session messages list retrieval."""
    message_service_mock.get_messages_list.return_value = [
        create_message_response(
            message_id=TEST_MESSAGE_ID,
            role=MessageRole.USER,
            content="Hello",
        ),
        create_message_response(
            message_id=TEST_MESSAGE_ID_2,
            role=MessageRole.ASSISTANT,
            content="Hi there",
        ),
    ]

    response = client.get(
        f"/chat/sessions/{TEST_SESSION_ID}/messages?limit=20&offset=0"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 20
    assert data["offset"] == 0
    assert data["total"] == 2
    assert len(data["items"]) == 2

    assert data["items"][0]["id"] == str(TEST_MESSAGE_ID)
    assert data["items"][0]["role"] == "user"
    assert data["items"][0]["content"] == "Hello"

    assert data["items"][1]["id"] == str(TEST_MESSAGE_ID_2)
    assert data["items"][1]["role"] == "assistant"
    assert data["items"][1]["content"] == "Hi there"

    message_service_mock.get_messages_list.assert_awaited_once()

    user_id, session_id, filters = (
        message_service_mock.get_messages_list.await_args.args
    )

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID
    assert filters.limit == 20
    assert filters.offset == 0


def test_get_chat_session_messages_empty_success(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test successful empty chat session messages list retrieval."""
    message_service_mock.get_messages_list.return_value = []

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/messages")

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0

    message_service_mock.get_messages_list.assert_awaited_once()

    user_id, session_id, _ = message_service_mock.get_messages_list.await_args.args

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID


def test_get_chat_session_messages_with_filters_success(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test successful chat session messages list retrieval with filters."""
    message_service_mock.get_messages_list.return_value = [
        create_message_response(
            message_id=TEST_MESSAGE_ID,
            role=MessageRole.ASSISTANT,
            content="Matching message",
        )
    ]

    response = client.get(
        f"/chat/sessions/{TEST_SESSION_ID}/messages",
        params={
            "search": "matching",
            "role": "assistant",
            "provider": "test-provider",
            "model_name": "test-model",
            "limit": 5,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["id"] == str(TEST_MESSAGE_ID)
    assert item["role"] == "assistant"
    assert item["content"] == "Matching message"

    message_service_mock.get_messages_list.assert_awaited_once()

    user_id, session_id, filters = (
        message_service_mock.get_messages_list.await_args.args
    )

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID
    assert filters.search == "matching"
    assert filters.role == MessageRole.ASSISTANT
    assert filters.provider == "test-provider"
    assert filters.model_name == "test-model"
    assert filters.limit == 5
    assert filters.offset == 0


def test_get_chat_session_messages_uses_current_user_id(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test that chat session messages retrieval passes current user id to service."""
    message_service_mock.get_messages_list.return_value = []

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/messages")

    assert response.status_code == 200

    message_service_mock.get_messages_list.assert_awaited_once()

    user_id, session_id, _ = message_service_mock.get_messages_list.await_args.args

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID
