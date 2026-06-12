"""Tests for user repository."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import User
except ImportError:
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories.user import UserRepository


def create_user(
    *,
    email: str = "test-user@example.com",
    username: str | None = "test_user",
    hashed_password: str = "test-password-hash",  # noqa: S107
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    """Create a user instance for repository tests.

    Args:
        email (str): User email.
        username (str | None): Optional username.
        hashed_password (str): Hashed user password.
        is_active (bool): Whether the user is active.
        is_superuser (bool): Whether the user is a superuser.

    Returns:
        User: User model instance.
    """
    return User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        is_active=is_active,
        is_superuser=is_superuser,
    )


@pytest.mark.asyncio
async def test_create_user_success(async_session: AsyncSession) -> None:
    """Test successful user creation."""
    repository = UserRepository(session=async_session)

    user = create_user(
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    created_user = await repository.create(user)

    assert created_user.id is not None
    assert created_user.email == "test-user@example.com"
    assert created_user.username == "test_user"
    assert created_user.hashed_password == "test-password-hash"  # noqa: S105
    assert created_user.is_active is True
    assert created_user.is_superuser is False


@pytest.mark.asyncio
async def test_create_user_without_username_success(
    async_session: AsyncSession,
) -> None:
    """Test successful user creation without username."""
    repository = UserRepository(session=async_session)

    user = create_user(
        email="no-username@example.com",
        username=None,
    )

    created_user = await repository.create(user)

    assert created_user.id is not None
    assert created_user.email == "no-username@example.com"
    assert created_user.username is None
    assert created_user.hashed_password == "test-password-hash"  # noqa: S105
    assert created_user.is_active is True
    assert created_user.is_superuser is False


@pytest.mark.asyncio
async def test_create_user_with_inactive_status_success(
    async_session: AsyncSession,
) -> None:
    """Test successful inactive user creation."""
    repository = UserRepository(session=async_session)

    user = create_user(
        email="inactive@example.com",
        username="inactive_user",
        is_active=False,
    )

    created_user = await repository.create(user)

    assert created_user.id is not None
    assert created_user.email == "inactive@example.com"
    assert created_user.username == "inactive_user"
    assert created_user.is_active is False
    assert created_user.is_superuser is False


@pytest.mark.asyncio
async def test_create_superuser_success(async_session: AsyncSession) -> None:
    """Test successful superuser creation."""
    repository = UserRepository(session=async_session)

    user = create_user(
        email="admin@example.com",
        username="admin",
        is_superuser=True,
    )

    created_user = await repository.create(user)

    assert created_user.id is not None
    assert created_user.email == "admin@example.com"
    assert created_user.username == "admin"
    assert created_user.is_active is True
    assert created_user.is_superuser is True


@pytest.mark.asyncio
async def test_create_user_defaults_success(async_session: AsyncSession) -> None:
    """Test successful user creation with model default values."""
    repository = UserRepository(session=async_session)

    user = User(
        email="defaults@example.com",
        username="defaults_user",
        hashed_password="test-password-hash",  # noqa: S106  # noqa: S106
    )

    created_user = await repository.create(user)

    assert created_user.id is not None
    assert created_user.email == "defaults@example.com"
    assert created_user.username == "defaults_user"
    assert created_user.hashed_password == "test-password-hash"  # noqa: S105
    assert created_user.is_active is True
    assert created_user.is_superuser is False


@pytest.mark.asyncio
async def test_get_user_by_id_success(async_session: AsyncSession) -> None:
    """Test successful user retrieval by identifier."""
    repository = UserRepository(session=async_session)

    created_user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
        )
    )

    user = await repository.get_by_id(created_user.id)

    assert user is not None
    assert user.id == created_user.id
    assert user.email == "test-user@example.com"
    assert user.username == "test_user"
    assert user.hashed_password == "test-password-hash"  # noqa: S105
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(async_session: AsyncSession) -> None:
    """Test that user retrieval by identifier returns None when not found."""
    repository = UserRepository(session=async_session)

    user = await repository.get_by_id(uuid4())

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id_returns_exact_user(
    async_session: AsyncSession,
) -> None:
    """Test that retrieval by identifier returns the exact matching user."""
    repository = UserRepository(session=async_session)

    first_user = await repository.create(
        create_user(
            email="first@example.com",
            username="first_user",
        )
    )

    second_user = await repository.create(
        create_user(
            email="second@example.com",
            username="second_user",
        )
    )

    found_user = await repository.get_by_id(second_user.id)

    assert found_user is not None
    assert found_user.id == second_user.id
    assert found_user.email == "second@example.com"
    assert found_user.username == "second_user"
    assert found_user.id != first_user.id


@pytest.mark.asyncio
async def test_get_user_by_email_success(async_session: AsyncSession) -> None:
    """Test successful user retrieval by email."""
    repository = UserRepository(session=async_session)

    created_user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
        )
    )

    user = await repository.get_by_email("test-user@example.com")

    assert user is not None
    assert user.id == created_user.id
    assert user.email == "test-user@example.com"
    assert user.username == "test_user"
    assert user.hashed_password == "test-password-hash"  # noqa: S105
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(async_session: AsyncSession) -> None:
    """Test that user retrieval by email returns None when not found."""
    repository = UserRepository(session=async_session)

    user = await repository.get_by_email("unknown@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email_returns_exact_user(
    async_session: AsyncSession,
) -> None:
    """Test that retrieval by email returns the exact matching user."""
    repository = UserRepository(session=async_session)

    first_user = await repository.create(
        create_user(
            email="first@example.com",
            username="first_user",
        )
    )

    second_user = await repository.create(
        create_user(
            email="second@example.com",
            username="second_user",
        )
    )

    found_user = await repository.get_by_email("second@example.com")

    assert found_user is not None
    assert found_user.id == second_user.id
    assert found_user.email == "second@example.com"
    assert found_user.username == "second_user"
    assert found_user.id != first_user.id


@pytest.mark.asyncio
async def test_get_user_by_email_is_case_sensitive(
    async_session: AsyncSession,
) -> None:
    """Test that email retrieval uses exact case-sensitive comparison."""
    repository = UserRepository(session=async_session)

    await repository.create(
        create_user(
            email="user@example.com",
            username="test_user",
        )
    )

    user = await repository.get_by_email("USER@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_update_user_success(async_session: AsyncSession) -> None:
    """Test successful user update."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="old-email@example.com",
            username="old_user",
            hashed_password="old-password-hash",  # noqa: S106
            is_active=True,
            is_superuser=False,
        )
    )

    user.email = "new-email@example.com"
    user.username = "new_user"
    user.hashed_password = "new-password-hash"  # noqa: S105  # noqa: S105
    user.is_active = False
    user.is_superuser = True

    updated_user = await repository.update(user)

    assert updated_user.id == user.id
    assert updated_user.email == "new-email@example.com"
    assert updated_user.username == "new_user"
    assert updated_user.hashed_password == "new-password-hash"  # noqa: S105
    assert updated_user.is_active is False
    assert updated_user.is_superuser is True

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.id == user.id
    assert found_user.email == "new-email@example.com"
    assert found_user.username == "new_user"
    assert found_user.hashed_password == "new-password-hash"  # noqa: S105
    assert found_user.is_active is False
    assert found_user.is_superuser is True


@pytest.mark.asyncio
async def test_update_user_username_to_none_success(
    async_session: AsyncSession,
) -> None:
    """Test successful update of username to None."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
        )
    )

    user.username = None

    updated_user = await repository.update(user)

    assert updated_user.id == user.id
    assert updated_user.email == "test-user@example.com"
    assert updated_user.username is None

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.username is None


@pytest.mark.asyncio
async def test_update_user_active_status_success(
    async_session: AsyncSession,
) -> None:
    """Test successful user active status update."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
            is_active=True,
        )
    )

    user.is_active = False

    updated_user = await repository.update(user)

    assert updated_user.id == user.id
    assert updated_user.is_active is False

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.is_active is False


@pytest.mark.asyncio
async def test_update_user_superuser_status_success(
    async_session: AsyncSession,
) -> None:
    """Test successful user superuser status update."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
            is_superuser=False,
        )
    )

    user.is_superuser = True

    updated_user = await repository.update(user)

    assert updated_user.id == user.id
    assert updated_user.is_superuser is True

    found_user = await repository.get_by_id(user.id)

    assert found_user is not None
    assert found_user.is_superuser is True


@pytest.mark.asyncio
async def test_delete_user_success(async_session: AsyncSession) -> None:
    """Test successful user deletion."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
        )
    )

    await repository.delete(user)

    found_user = await repository.get_by_id(user.id)

    assert found_user is None


@pytest.mark.asyncio
async def test_delete_user_removes_database_row_success(
    async_session: AsyncSession,
) -> None:
    """Test that user deletion removes the database row."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="test-user@example.com",
            username="test_user",
        )
    )

    await repository.delete(user)

    result = await async_session.execute(select(User).where(User.id == user.id))
    stored_user = result.scalar_one_or_none()

    assert stored_user is None


@pytest.mark.asyncio
async def test_delete_user_does_not_delete_other_users(
    async_session: AsyncSession,
) -> None:
    """Test that deleting one user does not delete another user."""
    repository = UserRepository(session=async_session)

    deleted_user = await repository.create(
        create_user(
            email="deleted@example.com",
            username="deleted_user",
        )
    )

    remaining_user = await repository.create(
        create_user(
            email="remaining@example.com",
            username="remaining_user",
        )
    )

    await repository.delete(deleted_user)

    found_deleted_user = await repository.get_by_id(deleted_user.id)
    found_remaining_user = await repository.get_by_id(remaining_user.id)

    assert found_deleted_user is None
    assert found_remaining_user is not None
    assert found_remaining_user.id == remaining_user.id
    assert found_remaining_user.email == "remaining@example.com"
    assert found_remaining_user.username == "remaining_user"


@pytest.mark.asyncio
async def test_deleted_user_cannot_be_found_by_email(
    async_session: AsyncSession,
) -> None:
    """Test that deleted user cannot be retrieved by email."""
    repository = UserRepository(session=async_session)

    user = await repository.create(
        create_user(
            email="deleted@example.com",
            username="deleted_user",
        )
    )

    await repository.delete(user)

    found_user = await repository.get_by_email("deleted@example.com")

    assert found_user is None
