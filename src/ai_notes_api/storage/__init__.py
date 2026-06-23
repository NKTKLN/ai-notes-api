"""Storage package.

This package exports the shared MinIO client and document storage helper.
"""

from ai_notes_api.storage.client import minio_client
from ai_notes_api.storage.document_storage import DocumentStorage

__all__ = ["DocumentStorage", "minio_client"]
