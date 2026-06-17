"""Chat memory exception module.

This module defines application exceptions related to chat memory.
"""

from ai_notes_api.exceptions import AppException


class ChatMemoryNotFoundError(AppException):
    """Exception raised when chat memory is not found."""

    status_code: int = 404
    code: str = "CHAT_MEMORY_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the chat memory not found exception.

        Returns:
            None.
        """
        super().__init__("Chat memory not found")
