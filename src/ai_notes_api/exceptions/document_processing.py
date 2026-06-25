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


class InvalidChunkSizeError(AppException):
    """Exception raised when chunk_size is invalid."""

    status_code: int = 400
    code: str = "INVALID_CHUNK_SIZE"

    def __init__(self) -> None:
        """Initialize invalid chunk_size exception."""
        super().__init__("chunk_size должен быть > 0")


class InvalidOverlapError(AppException):
    """Exception raised when overlap is invalid."""

    status_code: int = 400
    code: str = "INVALID_OVERLAP"

    def __init__(self) -> None:
        """Initialize invalid overlap exception."""
        super().__init__("overlap должен быть >= 0")


class OverlapGreaterThanOrEqualChunkSizeError(AppException):
    """Exception raised when overlap is greater than or equal to chunk_size."""

    status_code: int = 400
    code: str = "OVERLAP_GREATER_THAN_OR_EQUAL_CHUNK_SIZE"

    def __init__(self) -> None:
        """Initialize overlap and chunk_size validation exception."""
        super().__init__("overlap должен быть меньше chunk_size")


class ChunkEmbeddingCountMismatchError(AppException):
    """Exception raised when chunk and embedding counts do not match."""

    status_code: int = 500
    code: str = "CHUNK_EMBEDDING_COUNT_MISMATCH"

    def __init__(self) -> None:
        """Initialize the chunk and embedding count mismatch exception."""
        super().__init__("Chunks and embeddings count mismatch")


class UnsupportedDocumentFormatError(AppException):
    """Exception raised when document format is not supported."""

    status_code: int = 415
    code: str = "UNSUPPORTED_DOCUMENT_FORMAT"

    def __init__(self, content_type: str | None = None) -> None:
        """Initialize unsupported document format exception."""
        message = "Unsupported document format"

        if content_type:
            message = f"Unsupported document format: {content_type}"

        super().__init__(message)
