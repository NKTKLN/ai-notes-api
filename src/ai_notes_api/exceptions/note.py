"""Note exception module.

This module defines application exceptions related to notes.
"""

from ai_notes_api.exceptions import AppException


class NoteNotFoundError(AppException):
    """Exception raised when a note is not found."""

    status_code: int = 404
    code: str = "NOTE_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the note not found exception."""
        super().__init__("Note not found")
