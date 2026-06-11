"""Chat session exception module.

This module defines application exceptions related to chat sessions.
"""

from ai_notes_api.exceptions import AppException


class ChatSessionNotFoundError(AppException):
    """Exception raised when a chat session is not found."""

    status_code: int = 404
    code: str = "CHAT_SESSION_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the chat session not found exception."""
        super().__init__("Chat session not found")
