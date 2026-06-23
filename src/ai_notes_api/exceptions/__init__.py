"""Application exceptions package.

This package re-exports application exceptions and exception handler
registration utilities.
"""

from ai_notes_api.exceptions.base import AppException, register_exception_handlers
from ai_notes_api.exceptions.chat_memory import (
    ChatMemoryDependenciesNotConfiguredError,
    ChatMemoryNotFoundError,
    MemoryInProgressError,
)
from ai_notes_api.exceptions.chat_session import ChatSessionNotFoundError
from ai_notes_api.exceptions.generation_job import (
    GenerationInProgressError,
    GenerationNotFoundError,
)
from ai_notes_api.exceptions.message import MessageNotFoundError
from ai_notes_api.exceptions.note import NoteNotFoundError
from ai_notes_api.exceptions.token import InvalidTokenError
from ai_notes_api.exceptions.user import (
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
    "ChatMemoryNotFoundError",
    "MemoryInProgressError",
    "ChatMemoryDependenciesNotConfiguredError",
]
