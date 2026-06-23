"""Document storage module.

This module provides a storage helper for uploading, downloading, and deleting
documents in MinIO object storage.
"""

from datetime import timedelta
from io import BytesIO
from uuid import UUID

from loguru import logger
from minio import Minio

from ai_notes_api.core import settings


class DocumentStorage:
    """Object storage helper for documents.

    Args:
        client (Minio): MinIO client used to perform object storage operations.
    """

    def __init__(self, client: Minio) -> None:
        """Initialize the document storage helper.

        Args:
            client (Minio): MinIO client used to perform object storage
                operations.
        """
        self.client = client
        self.bucket = settings.minio_bucket_name

    def ensure_bucket(self) -> None:
        """Create the storage bucket if it does not already exist."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            logger.info("Storage bucket created: bucket={}", self.bucket)

    def build_object_name(
        self,
        user_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str:
        """Build the object name used to store a document.

        Args:
            user_id (UUID): Identifier of the user who owns the document.
            document_id (UUID): Unique document identifier.
            filename (str): Original document file name.

        Returns:
            str: Object name within the storage bucket.
        """
        return f"users/{user_id}/documents/{document_id}/original/{filename}"

    def upload_file(
        self,
        user_id: UUID,
        document_id: UUID,
        filename: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload a document to object storage.

        Args:
            user_id (UUID): Identifier of the user who owns the document.
            document_id (UUID): Unique document identifier.
            filename (str): Original document file name.
            data (bytes): Raw document content.
            content_type (str): MIME type of the document.

        Returns:
            str: Object name under which the document was stored.
        """
        self.ensure_bucket()

        object_name = self.build_object_name(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
        )

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

        logger.info(
            "Document uploaded: object_name={}, size={}",
            object_name,
            len(data),
        )

        return object_name

    def download_file(self, object_name: str) -> bytes:
        """Download a document from object storage.

        Args:
            object_name (str): Object name within the storage bucket.

        Returns:
            bytes: Raw document content.
        """
        response = self.client.get_object(self.bucket, object_name)

        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()

        logger.debug("Document downloaded: object_name={}", object_name)

        return data

    def get_presigned_download_url(
        self,
        object_name: str,
        expires_in_seconds: int | None = None,
    ) -> str:
        """Build a presigned URL for downloading a document.

        Args:
            object_name (str): Object name within the storage bucket.
            expires_in_seconds (int | None): Optional URL lifetime in seconds.
                Defaults to the configured presigned URL lifetime.

        Returns:
            str: Presigned URL used to download the document.
        """
        if expires_in_seconds is None:
            expires_in_seconds = settings.minio_presigned_url_expire_seconds

        url = self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=object_name,
            expires=timedelta(seconds=expires_in_seconds),
        )

        logger.debug(
            "Presigned download URL created: object_name={}, expires_in_seconds={}",
            object_name,
            expires_in_seconds,
        )

        return url

    def delete_file(self, object_name: str) -> None:
        """Delete a document from object storage.

        Args:
            object_name (str): Object name within the storage bucket.
        """
        self.client.remove_object(self.bucket, object_name)

        logger.info("Document deleted: object_name={}", object_name)
