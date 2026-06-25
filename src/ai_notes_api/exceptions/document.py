"""Document exception module.

This module defines application exceptions related to documents.
"""

from ai_notes_api.exceptions import AppException


class DocumentNotFoundError(AppException):
    """Exception raised when a document is not found."""

    status_code: int = 404
    code: str = "DOCUMENT_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the document not found exception."""
        super().__init__("Document not found")
