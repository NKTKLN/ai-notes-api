"""Generation exception module.

This module defines application exceptions related to LLM generation jobs.
"""

from ai_notes_api.exceptions import AppException


class GenerationInProgressError(AppException):
    """Exception raised when a generation job is already in progress."""

    status_code: int = 409
    code: str = "GENERATION_IN_PROGRESS"

    def __init__(self) -> None:
        """Initialize the generation in progress exception."""
        super().__init__("Generation already in progress")


class GenerationNotFoundError(AppException):
    """Exception raised when a generation job is not found."""

    status_code: int = 404
    code: str = "GENERATION_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the generation not found exception."""
        super().__init__("Generation not found")


class GenerationMessageMissingError(AppException):
    """Exception raised when a completion does not return a persisted message."""

    status_code: int = 500
    code: str = "GENERATION_MESSAGE_MISSING"

    def __init__(self) -> None:
        """Initialize the generation message missing exception."""
        super().__init__("Completion did not return a persisted message id")
