"""Application exceptions package.

This package re-exports application exceptions and exception handler
registration utilities.
"""

from .base import AppException, register_exception_handlers
from .chat_session import ChatSessionNotFoundError
from .generation_job import GenerationInProgressError, GenerationNotFoundError
from .message import MessageNotFoundError
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
    "ChatSessionNotFoundError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "MessageNotFoundError",
    "NoteNotFoundError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "register_exception_handlers",
    "GenerationInProgressError",
    "GenerationNotFoundError",
]
