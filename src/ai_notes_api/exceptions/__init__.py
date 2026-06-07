"""Application exceptions package.

This package re-exports application exceptions and exception handler
registration utilities.
"""

from .base import AppException, register_exception_handlers
from .note import NoteNotFoundError

__all__ = [
    "AppException",
    "NoteNotFoundError",
    "register_exception_handlers",
]
