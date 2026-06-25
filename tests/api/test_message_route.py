"""Tests for messages API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.dependencies import get_current_user, get_message_service
from ai_notes_api.api.v1.messages import router
from ai_notes_api.db.models import MessageRole, User
from ai_notes_api.schemas import MessageResponseSchema

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_MESSAGE_ID = UUID("33333333-3333-3333-3333-333333333333")


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


def create_message_response(
    *,
    message_id: UUID = TEST_MESSAGE_ID,
    role: MessageRole = MessageRole.USER,
    content: str = "Test message",
    provider: str | None = None,
    model_name: str | None = None,
) -> MessageResponseSchema:
    """Create message response schema for router tests.

    Args:
        message_id (UUID): Unique message identifier.
        role (MessageRole): Message role.
        content (str): Message content.
        provider (str | None): Optional AI provider name.
        model_name (str | None): Optional AI model name.

    Returns:
        MessageResponseSchema: Message response schema instance.
    """
    return MessageResponseSchema(
        id=message_id,
        session_id=TEST_SESSION_ID,
        role=role,
        content=content,
        provider=provider,
        model_name=model_name,
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
def message_service_mock() -> AsyncMock:
    """Create mocked message service.

    Returns:
        AsyncMock: Mocked message service dependency.
    """
    return AsyncMock()


@pytest.fixture
def client(
    message_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        message_service_mock (AsyncMock): Mocked message service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_message_service] = lambda: message_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_get_message_success(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test successful message retrieval by identifier."""
    message_service_mock.get_message.return_value = create_message_response(
        message_id=TEST_MESSAGE_ID,
        role=MessageRole.ASSISTANT,
        content="Hi there",
        provider="test-provider",
        model_name="test-model",
    )

    response = client.get(f"/chat/messages/{TEST_MESSAGE_ID}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_MESSAGE_ID)
    assert data["session_id"] == str(TEST_SESSION_ID)
    assert data["role"] == MessageRole.ASSISTANT.value
    assert data["content"] == "Hi there"
    assert data["provider"] == "test-provider"
    assert data["model_name"] == "test-model"

    message_service_mock.get_message.assert_awaited_once_with(
        TEST_USER_ID, TEST_MESSAGE_ID
    )


def test_delete_message_success(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test successful message deletion."""
    message_service_mock.delete_message.return_value = None

    response = client.delete(f"/chat/messages/{TEST_MESSAGE_ID}")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    message_service_mock.delete_message.assert_awaited_once_with(
        TEST_USER_ID, TEST_MESSAGE_ID
    )


def test_get_message_uses_current_user_id(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test that message retrieval passes current user id to service."""
    message_service_mock.get_message.return_value = create_message_response(
        message_id=TEST_MESSAGE_ID
    )

    response = client.get(f"/chat/messages/{TEST_MESSAGE_ID}")

    assert response.status_code == 200

    message_service_mock.get_message.assert_awaited_once_with(
        TEST_USER_ID, TEST_MESSAGE_ID
    )


def test_delete_message_uses_current_user_id(
    client: TestClient,
    message_service_mock: AsyncMock,
) -> None:
    """Test that message deletion passes current user id to service."""
    message_service_mock.delete_message.return_value = None

    response = client.delete(f"/chat/messages/{TEST_MESSAGE_ID}")

    assert response.status_code == 200

    message_service_mock.delete_message.assert_awaited_once_with(
        TEST_USER_ID, TEST_MESSAGE_ID
    )
