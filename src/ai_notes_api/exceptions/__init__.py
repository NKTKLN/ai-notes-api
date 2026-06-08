"""Application exceptions package.

This package re-exports application exceptions and exception handler
registration utilities.
"""

from .base import AppException, register_exception_handlers
from .note import NoteNotFoundError
from .token import InvalidTokenError
from .user import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

__all__ = [
    "AppException",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "NoteNotFoundError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "register_exception_handlers",
]
