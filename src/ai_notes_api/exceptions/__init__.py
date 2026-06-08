"""Application exceptions package.

This package re-exports application exceptions and exception handler
registration utilities.
"""

from .base import AppException, register_exception_handlers
from .note import NoteNotFoundError
from .token import InvalidTokenError

__all__ = [
    "AppException",
    "InvalidTokenError",
    "NoteNotFoundError",
    "register_exception_handlers",
]
