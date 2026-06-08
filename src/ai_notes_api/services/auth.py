"""Authentication service module.

This module provides business logic for user registration, authentication,
and access token creation.
"""

from ai_notes_api.core import create_access_token, hash_password, verify_password
from ai_notes_api.db.models import User
from ai_notes_api.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from ai_notes_api.repositories import UserRepository
from ai_notes_api.schemas import UserCreateSchema


class AuthService:
    """Service for authentication-related business operations.

    Args:
        repository (UserRepository): User repository used by the service.

    Attributes:
        repository (UserRepository): User repository used by the service.
    """

    def __init__(self, repository: UserRepository) -> None:
        """Initialize the authentication service.

        Args:
            repository (UserRepository): User repository used by the service.
        """
        self.repository = repository

    async def register_user(self, data: UserCreateSchema) -> User:
        """Register a new user.

        Args:
            data (UserCreateSchema): Validated user registration data.

        Returns:
            User: Created user.

        Raises:
            UserAlreadyExistsError: If a user with the given email already
                exists.
        """
        existing_user = await self.repository.get_by_email(data.email)

        if existing_user is not None:
            raise UserAlreadyExistsError()

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )

        return await self.repository.create(user)

    async def authenticate_user(self, email: str, password: str) -> User:
        """Authenticate a user by email and password.

        Args:
            email (str): User email address.
            password (str): Raw user password.

        Returns:
            User: Authenticated active user.

        Raises:
            InvalidCredentialsError: If the email or password is invalid.
            InactiveUserError: If the user account is inactive.
        """
        user = await self.repository.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InactiveUserError()

        return user

    async def get_user(self, user_id: int) -> User:
        """Return a user by its identifier.

        Args:
            user_id (int): Unique user identifier.

        Returns:
            User: Matching user.

        Raises:
            UserNotFoundError: If no user with the given identifier exists.
        """
        user = await self.repository.get_by_id(user_id)

        if user is None:
            raise UserNotFoundError()

        return user

    def create_token_for_user(self, user: User) -> str:
        """Create an access token for a user.

        Args:
            user (User): User to create an access token for.

        Returns:
            str: Encoded JWT access token.
        """
        return create_access_token(subject=str(user.id))
