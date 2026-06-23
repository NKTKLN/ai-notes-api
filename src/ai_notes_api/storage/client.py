"""MinIO client module.

This module defines a shared MinIO client configured from application settings.
"""

from minio import Minio

from ai_notes_api.core import settings

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)
