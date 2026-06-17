"""Chat memory exception module.

This module defines application exceptions related to chat memory.
"""

from ai_notes_api.exceptions import AppException


class ChatMemoryNotFoundError(AppException):
    """Exception raised when chat memory is not found.

    Attributes:
        status_code (int): HTTP status code returned for this exception.
        code (str): Application-specific error code.
    """

    status_code: int = 404
    code: str = "CHAT_MEMORY_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the chat memory not found exception."""
        super().__init__("Chat memory not found")


class MemoryInProgressError(AppException):
    """Exception raised when chat memory summarization is already in progress.

    Attributes:
        status_code (int): HTTP status code returned for this exception.
        code (str): Application-specific error code.
    """

    status_code: int = 409
    code: str = "MEMORY_IN_PROGRESS"

    def __init__(self) -> None:
        """Initialize the memory in progress exception."""
        super().__init__("Chat memory summarization is already in progress")
