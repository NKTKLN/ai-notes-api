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

__all__ = [
    "ErrorResponseSchema",
    "NoteCreateSchema",
    "NoteListQuerySchema",
    "NoteListResponseSchema",
    "NoteResponseSchema",
    "NoteUpdateSchema",
    "StatusResponseSchema",
]
