"""User exception module.

This module defines application exceptions related to users.
"""

from ai_notes_api.exceptions import AppException


class UserAlreadyExistsError(AppException):
    """Exception raised when a user already exists."""

    status_code: int = 409
    code: str = "USER_ALREADY_EXISTS"

    def __init__(self) -> None:
        """Initialize the user already exists exception."""
        super().__init__("User already exists")


class UserNotFoundError(AppException):
    """Exception raised when a user is not found."""

    status_code: int = 404
    code: str = "USER_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the user not found exception."""
        super().__init__("User not found")


class InvalidCredentialsError(AppException):
    """Exception raised when user credentials are invalid."""

    status_code: int = 401
    code: str = "INVALID_CREDENTIALS"

    def __init__(self) -> None:
        """Initialize the invalid credentials exception."""
        super().__init__("Invalid email or password")


class InactiveUserError(AppException):
    """Exception raised when a user account is inactive."""

    status_code: int = 403
    code: str = "INACTIVE_USER"

    def __init__(self) -> None:
        """Initialize the inactive user exception."""
        super().__init__("User account is inactive")
