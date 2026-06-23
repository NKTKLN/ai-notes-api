"""Storage package.

This package exports the shared S3 client factory and document storage helper.
"""

from ai_notes_api.storage.client import get_s3_client
from ai_notes_api.storage.document_storage import DocumentStorage

__all__ = ["DocumentStorage", "get_s3_client"]
