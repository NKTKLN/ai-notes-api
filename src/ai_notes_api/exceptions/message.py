"""Message exception module.

This module defines application exceptions related to messages.
"""

from ai_notes_api.exceptions import AppException


class MessageNotFoundError(AppException):
    """Exception raised when a message is not found."""

    status_code: int = 404
    code: str = "MESSAGE_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the message not found exception."""
        super().__init__("Message not found")
