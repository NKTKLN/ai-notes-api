"""Authentication exception module.

This module defines application exceptions related to authentication.
"""

from ai_notes_api.exceptions.base import AppException


class InvalidTokenError(AppException):
    """Exception raised when an authentication token is invalid."""

    status_code: int = 401
    code: str = "INVALID_TOKEN"

    def __init__(self) -> None:
        """Initialize the invalid token exception."""
        super().__init__("Invalid authentication credentials")
