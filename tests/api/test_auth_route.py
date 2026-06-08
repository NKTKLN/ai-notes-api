"""Tests for authentication API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.auth import router
from ai_notes_api.api.v1.dependencies import get_auth_service, get_current_user
from ai_notes_api.db.models import User
from ai_notes_api.services import AuthService


def create_test_user(  # noqa: PLR0913
    *,
    user_id: int = 1,
    email: str = "test-user@example.com",
    username: str | None = "test_user",
    hashed_password: str = "test-password-hash",  # noqa: S107
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    """Create test user for router tests.

    Args:
        user_id (int): Unique user identifier.
        email (str): User email.
        username (str | None): Optional username.
        hashed_password (str): Hashed user password.
        is_active (bool): Whether the user is active.
        is_superuser (bool): Whether the user is a superuser.

    Returns:
        User: Test user model instance.
    """
    now = datetime.now(UTC)

    return User(
        id=user_id,
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=is_active,
        is_superuser=is_superuser,
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
def auth_service_mock() -> Mock:
    """Create mocked auth service.

    Returns:
        Mock: Mocked auth service dependency.
    """
    service = Mock(spec=AuthService)
    service.register_user = AsyncMock()
    service.authenticate_user = AsyncMock()
    service.create_token_for_user = Mock()
    return service


@pytest.fixture
def client(
    auth_service_mock: Mock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        auth_service_mock (Mock): Mocked auth service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_auth_service] = lambda: auth_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_register_user_success(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test successful user registration."""
    auth_service_mock.register_user.return_value = create_test_user(
        user_id=1,
        email="user@example.com",
        username="testuser",
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "username": "testuser",
            "password": "password",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["email"] == "user@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True
    assert "hashed_password" not in data
    assert "password" not in data

    auth_service_mock.register_user.assert_awaited_once()

    register_data = auth_service_mock.register_user.await_args.args[0]

    assert register_data.email == "user@example.com"
    assert register_data.username == "testuser"
    assert register_data.password == "password"  # noqa: S105


def test_register_user_without_username_success(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test successful user registration without username."""
    auth_service_mock.register_user.return_value = create_test_user(
        user_id=1,
        email="user@example.com",
        username=None,
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "user@example.com",
            "username": None,
            "password": "password",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["email"] == "user@example.com"
    assert data["username"] is None
    assert data["is_active"] is True

    auth_service_mock.register_user.assert_awaited_once()

    register_data = auth_service_mock.register_user.await_args.args[0]

    assert register_data.email == "user@example.com"
    assert register_data.username is None
    assert register_data.password == "password"  # noqa: S105


def test_register_user_invalid_payload(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test that user registration validates request payload."""
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "username": "testuser",
        },
    )

    assert response.status_code == 422

    auth_service_mock.register_user.assert_not_awaited()


def test_login_user_success(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test successful user login."""
    user = create_test_user(
        user_id=1,
        email="user@example.com",
        username="testuser",
    )
    auth_service_mock.authenticate_user.return_value = user
    auth_service_mock.create_token_for_user.return_value = "access-token"

    response = client.post(
        "/auth/login",
        data={
            "username": "user@example.com",
            "password": "password",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"] == "access-token"  # noqa: S105
    assert data["token_type"] == "bearer"  # noqa: S105

    auth_service_mock.authenticate_user.assert_awaited_once_with(
        "user@example.com",
        "password",
    )
    auth_service_mock.create_token_for_user.assert_called_once_with(user)


def test_login_user_uses_oauth_username_as_email(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test that login passes OAuth username field as email to service."""
    user = create_test_user(
        user_id=1,
        email="user@example.com",
        username="testuser",
    )
    auth_service_mock.authenticate_user.return_value = user
    auth_service_mock.create_token_for_user.return_value = "access-token"

    response = client.post(
        "/auth/login",
        data={
            "username": "user@example.com",
            "password": "password",
        },
    )

    assert response.status_code == 200

    auth_service_mock.authenticate_user.assert_awaited_once()

    email, password = auth_service_mock.authenticate_user.await_args.args

    assert email == "user@example.com"
    assert password == "password"  # noqa: S105


def test_login_user_missing_username(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test that login validates missing username."""
    response = client.post(
        "/auth/login",
        data={
            "password": "password",
        },
    )

    assert response.status_code == 422

    auth_service_mock.authenticate_user.assert_not_awaited()
    auth_service_mock.create_token_for_user.assert_not_called()


def test_login_user_missing_password(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test that login validates missing password."""
    response = client.post(
        "/auth/login",
        data={
            "username": "user@example.com",
        },
    )

    assert response.status_code == 422

    auth_service_mock.authenticate_user.assert_not_awaited()
    auth_service_mock.create_token_for_user.assert_not_called()


def test_get_current_user_profile_success(
    client: TestClient,
    current_user: User,
) -> None:
    """Test successful current user profile retrieval."""
    response = client.get("/auth/me")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == current_user.id
    assert data["email"] == current_user.email
    assert data["username"] == current_user.username
    assert data["is_active"] is True
    assert "hashed_password" not in data
    assert "password" not in data


def test_get_current_user_profile_with_nullable_username_success(
    auth_service_mock: Mock,
) -> None:
    """Test successful current user profile retrieval without username."""
    current_user = create_test_user(
        user_id=1,
        email="user@example.com",
        username=None,
    )

    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_auth_service] = lambda: auth_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    client = TestClient(app)

    response = client.get("/auth/me")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["email"] == "user@example.com"
    assert data["username"] is None
    assert data["is_active"] is True


def test_get_current_user_profile_does_not_use_auth_service(
    client: TestClient,
    auth_service_mock: Mock,
) -> None:
    """Test that current user profile endpoint uses current user dependency."""
    response = client.get("/auth/me")

    assert response.status_code == 200

    auth_service_mock.register_user.assert_not_awaited()
    auth_service_mock.authenticate_user.assert_not_awaited()
    auth_service_mock.create_token_for_user.assert_not_called()
