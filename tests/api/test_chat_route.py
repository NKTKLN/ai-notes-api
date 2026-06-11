"""Tests for chat API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.chat import router
from ai_notes_api.api.v1.dependencies import (
    get_chat_session_service,
    get_current_user,
)
from ai_notes_api.db.models import User
from ai_notes_api.schemas import ChatSessionResponseSchema


def create_test_user() -> User:
    """Create current user for router tests.

    Returns:
        User: Test user model instance.
    """
    return User(
        id=1,
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )


def create_chat_session_response(
    *,
    session_id: int = 1,
    title: str = "Test chat session",
) -> ChatSessionResponseSchema:
    """Create chat session response schema for router tests.

    Args:
        session_id (int): Unique chat session identifier.
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
def client(
    chat_session_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        chat_session_service_mock (AsyncMock): Mocked chat session service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_chat_session_service] = lambda: (
        chat_session_service_mock
    )
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_create_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session creation."""
    chat_session_service_mock.create_chat_session.return_value = (
        create_chat_session_response(
            session_id=1,
            title="Test session",
        )
    )

    response = client.post(
        "/chat",
        json={
            "title": "Test session",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == "Test session"

    chat_session_service_mock.create_chat_session.assert_awaited_once()

    user_id, create_data = chat_session_service_mock.create_chat_session.await_args.args

    assert user_id == 1
    assert create_data.title == "Test session"


def test_get_chat_sessions_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat sessions list retrieval."""
    chat_session_service_mock.get_list.return_value = [
        create_chat_session_response(
            session_id=2,
            title="Second session",
        ),
        create_chat_session_response(
            session_id=1,
            title="First session",
        ),
    ]

    response = client.get("/chat?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 2
    assert len(data["items"]) == 2

    assert data["items"][0]["id"] == 2
    assert data["items"][0]["title"] == "Second session"

    assert data["items"][1]["id"] == 1
    assert data["items"][1]["title"] == "First session"

    chat_session_service_mock.get_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_list.await_args.args

    assert user_id == 1
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_chat_sessions_empty_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful empty chat sessions list retrieval."""
    chat_session_service_mock.get_list.return_value = []

    response = client.get("/chat?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 0

    chat_session_service_mock.get_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_list.await_args.args

    assert user_id == 1
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_chat_sessions_with_filters_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat sessions list retrieval with filters."""
    chat_session_service_mock.get_list.return_value = [
        create_chat_session_response(
            session_id=1,
            title="Matching session",
        )
    ]

    response = client.get(
        "/chat",
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

    assert item["id"] == 1
    assert item["title"] == "Matching session"

    chat_session_service_mock.get_list.assert_awaited_once()

    user_id, filters = chat_session_service_mock.get_list.await_args.args

    assert user_id == 1
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
            session_id=1,
            title="Test session",
        )
    )

    response = client.get("/chat/1")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == "Test session"

    chat_session_service_mock.get_chat_session.assert_awaited_once_with(1, 1)


def test_update_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session update."""
    chat_session_service_mock.update_chat_session.return_value = (
        create_chat_session_response(
            session_id=1,
            title="Updated session",
        )
    )

    response = client.patch(
        "/chat/1",
        json={
            "title": "Updated session",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["title"] == "Updated session"

    chat_session_service_mock.update_chat_session.assert_awaited_once()

    user_id, session_id, update_data = (
        chat_session_service_mock.update_chat_session.await_args.args
    )

    assert user_id == 1
    assert session_id == 1
    assert update_data.title == "Updated session"


def test_delete_chat_session_success(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test successful chat session deletion."""
    chat_session_service_mock.delete_chat_session.return_value = None

    response = client.delete("/chat/1")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    chat_session_service_mock.delete_chat_session.assert_awaited_once_with(1, 1)


def test_create_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session creation passes current user id to service."""
    chat_session_service_mock.create_chat_session.return_value = (
        create_chat_session_response(session_id=1)
    )

    response = client.post(
        "/chat",
        json={
            "title": "Test chat session",
        },
    )

    assert response.status_code == 201

    chat_session_service_mock.create_chat_session.assert_awaited_once()

    user_id, _ = chat_session_service_mock.create_chat_session.await_args.args

    assert user_id == 1


def test_get_chat_sessions_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat sessions list retrieval passes current user id to service."""
    chat_session_service_mock.get_list.return_value = []

    response = client.get("/chat")

    assert response.status_code == 200

    chat_session_service_mock.get_list.assert_awaited_once()

    user_id, _ = chat_session_service_mock.get_list.await_args.args

    assert user_id == 1


def test_get_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session retrieval passes current user id to service."""
    chat_session_service_mock.get_chat_session.return_value = (
        create_chat_session_response(session_id=1)
    )

    response = client.get("/chat/1")

    assert response.status_code == 200

    chat_session_service_mock.get_chat_session.assert_awaited_once_with(1, 1)


def test_update_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session update passes current user id to service."""
    chat_session_service_mock.update_chat_session.return_value = (
        create_chat_session_response(
            session_id=1,
            title="Updated session",
        )
    )

    response = client.patch(
        "/chat/1",
        json={
            "title": "Updated session",
        },
    )

    assert response.status_code == 200

    chat_session_service_mock.update_chat_session.assert_awaited_once()

    user_id, session_id, _ = (
        chat_session_service_mock.update_chat_session.await_args.args
    )

    assert user_id == 1
    assert session_id == 1


def test_delete_chat_session_uses_current_user_id(
    client: TestClient,
    chat_session_service_mock: AsyncMock,
) -> None:
    """Test that chat session deletion passes current user id to service."""
    chat_session_service_mock.delete_chat_session.return_value = None

    response = client.delete("/chat/1")

    assert response.status_code == 200

    chat_session_service_mock.delete_chat_session.assert_awaited_once_with(1, 1)
