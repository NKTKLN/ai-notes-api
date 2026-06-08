"""API schemas package.

This package re-exports schema classes used by the API.
"""

from .error import ErrorResponseSchema
from .note import (
    NoteCreateSchema,
    NoteListQuerySchema,
    NoteListResponseSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
)
from .status import StatusResponseSchema
from .token import TokenResponseSchema
from .user import LoginRequestSchema, UserCreateSchema, UserResponseSchema

__all__ = [
    "ErrorResponseSchema",
    "LoginRequestSchema",
    "NoteCreateSchema",
    "NoteListQuerySchema",
    "NoteListResponseSchema",
    "NoteResponseSchema",
    "NoteUpdateSchema",
    "StatusResponseSchema",
    "TokenResponseSchema",
    "UserCreateSchema",
    "UserResponseSchema",
]
