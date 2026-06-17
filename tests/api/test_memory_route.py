"""Tests for chat session memory API endpoint."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.chat_sessions import router
from ai_notes_api.api.v1.dependencies import get_current_user, get_memory_service
from ai_notes_api.db.models import User
from ai_notes_api.exceptions import ChatMemoryNotFoundError
from ai_notes_api.exceptions.base import register_exception_handlers
from ai_notes_api.schemas import ChatMemoryResponseSchema

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_SESSION_ID = UUID("22222222-2222-2222-2222-222222222222")


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


def create_memory_response() -> ChatMemoryResponseSchema:
    """Create chat memory response schema for router tests.

    Returns:
        ChatMemoryResponseSchema: Chat memory response schema instance.
    """
    now = datetime.now(UTC)

    return ChatMemoryResponseSchema(
        session_id=TEST_SESSION_ID,
        summary="Test summary",
        facts=[{"key": "name", "value": "Alex"}],
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def memory_service_mock() -> AsyncMock:
    """Create mocked chat memory service.

    Returns:
        AsyncMock: Mocked chat memory service dependency.
    """
    return AsyncMock()


@pytest.fixture
def client(
    memory_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        memory_service_mock (AsyncMock): Mocked chat memory service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    register_exception_handlers(app)

    app.dependency_overrides[get_memory_service] = lambda: memory_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_get_chat_session_memory_success(
    client: TestClient,
    memory_service_mock: AsyncMock,
) -> None:
    """Test successful chat session memory retrieval."""
    memory_service_mock.get_by_session_id.return_value = create_memory_response()

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/memory")

    assert response.status_code == 200

    data = response.json()

    assert data["session_id"] == str(TEST_SESSION_ID)
    assert data["summary"] == "Test summary"
    assert data["facts"] == [{"key": "name", "value": "Alex"}]

    memory_service_mock.get_by_session_id.assert_awaited_once()

    user_id, session_id = memory_service_mock.get_by_session_id.await_args.args

    assert user_id == TEST_USER_ID
    assert session_id == TEST_SESSION_ID


def test_get_chat_session_memory_not_found(
    client: TestClient,
    memory_service_mock: AsyncMock,
) -> None:
    """Test that retrieving missing chat memory returns a 404 error."""
    memory_service_mock.get_by_session_id.side_effect = ChatMemoryNotFoundError()

    response = client.get(f"/chat/sessions/{TEST_SESSION_ID}/memory")

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Chat memory not found"
