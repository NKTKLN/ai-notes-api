"""Document processing job exception module.

This module defines application exceptions related to document processing jobs.
"""

from ai_notes_api.exceptions import AppException


class DocumentProcessingJobNotFoundError(AppException):
    """Exception raised when a document processing job is not found."""

    status_code: int = 404
    code: str = "DOCUMENT_PROCESSING_JOB_NOT_FOUND"

    def __init__(self) -> None:
        """Initialize the document processing job not found exception."""
        super().__init__("Document processing job not found")
