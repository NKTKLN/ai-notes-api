"""Tests for authentication service."""

from typing import cast

import pytest

from ai_notes_api.db.models import User
from ai_notes_api.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ai_notes_api.repositories import UserRepository
from ai_notes_api.schemas import UserCreateSchema
from ai_notes_api.services import AuthService


class FakeUserRepository:
    """Fake user repository used for testing auth service behavior.

    Attributes:
        users (dict[int, User]): In-memory storage of users by identifier.
        created_user (User | None): Last user created through the fake repository.
    """

    def __init__(self) -> None:
        """Initialize the fake user repository."""
        self.users: dict[int, User] = {}
        self.created_user: User | None = None

    async def create(self, user: User) -> User:
        """Create a user in the fake repository.

        Args:
            user (User): User instance to create.

        Returns:
            User: Created user with assigned identifier.
        """
        user.id = 1

        if user.is_active is None:
            user.is_active = True

        if user.is_superuser is None:
            user.is_superuser = False

        self.created_user = user
        self.users[user.id] = user
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Return a user by its identifier.

        Args:
            user_id (int): Unique user identifier.

        Returns:
            User | None: Matching user if found; otherwise, None.
        """
        return self.users.get(user_id)

    async def get_by_email(self, user_email: str) -> User | None:
        """Return a user by its email.

        Args:
            user_email (str): User email.

        Returns:
            User | None: Matching user if found; otherwise, None.
        """
        for user in self.users.values():
            if user.email == user_email:
                return user

        return None

    async def update(self, user: User) -> User:
        """Update a user in the fake repository.

        Args:
            user (User): User instance with updated values.

        Returns:
            User: Updated user.
        """
        self.users[user.id] = user
        return user

    async def delete(self, user: User) -> None:
        """Delete a user from the fake repository.

        Args:
            user (User): User instance to delete.
        """
        del self.users[user.id]


@pytest.mark.asyncio
async def test_register_user_success() -> None:
    """Test successful user registration."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    data = UserCreateSchema(
        email="user@example.com",
        username="testuser",
        password="password",  # noqa: S106
    )

    user = await service.register_user(data)

    assert user.id == 1
    assert user.email == "user@example.com"
    assert user.username == "testuser"
    assert user.hashed_password != "password"  # noqa: S105
    assert repository.created_user == user


@pytest.mark.asyncio
async def test_register_user_already_exists() -> None:
    """Test that registration raises an error when user already exists."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    repository.users[1] = User(
        id=1,
        email="user@example.com",
        username="existinguser",
        hashed_password="hashed-password",  # noqa: S106
    )

    data = UserCreateSchema(
        email="user@example.com",
        username="testuser",
        password="password",  # noqa: S106
    )

    with pytest.raises(UserAlreadyExistsError):
        await service.register_user(data)


@pytest.mark.asyncio
async def test_authenticate_user_success() -> None:
    """Test successful user authentication."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    data = UserCreateSchema(
        email="user@example.com",
        username="testuser",
        password="password",  # noqa: S106
    )
    registered_user = await service.register_user(data)

    user = await service.authenticate_user("user@example.com", "password")

    assert user.id == registered_user.id
    assert user.email == "user@example.com"
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_email() -> None:
    """Test that authentication raises an error for unknown email."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user("unknown@example.com", "password")


@pytest.mark.asyncio
async def test_authenticate_user_invalid_password() -> None:
    """Test that authentication raises an error for invalid password."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    data = UserCreateSchema(
        email="user@example.com",
        username="testuser",
        password="password",  # noqa: S106
    )
    await service.register_user(data)

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate_user("user@example.com", "wrong-password")


@pytest.mark.asyncio
async def test_authenticate_user_inactive() -> None:
    """Test that authentication raises an error for inactive user."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    data = UserCreateSchema(
        email="user@example.com",
        username="testuser",
        password="password",  # noqa: S106
    )
    user = await service.register_user(data)
    user.is_active = False

    with pytest.raises(InactiveUserError):
        await service.authenticate_user("user@example.com", "password")


@pytest.mark.asyncio
async def test_get_user_success() -> None:
    """Test successful user retrieval by identifier."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    repository.users[1] = User(
        id=1,
        email="user@example.com",
        username="testuser",
        hashed_password="hashed-password",  # noqa: S106
    )

    user = await service.get_user(1)

    assert user.id == 1
    assert user.email == "user@example.com"
    assert user.username == "testuser"


@pytest.mark.asyncio
async def test_get_user_not_found() -> None:
    """Test that user retrieval raises an error when user is not found."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    with pytest.raises(UserNotFoundError):
        await service.get_user(999)


def test_create_token_for_user_success() -> None:
    """Test successful access token creation for user."""
    repository = FakeUserRepository()
    service = AuthService(repository=cast(UserRepository, repository))

    user = User(
        id=1,
        email="user@example.com",
        username="testuser",
        hashed_password="hashed-password",  # noqa: S106
    )

    token = service.create_token_for_user(user)

    assert isinstance(token, str)
    assert token
