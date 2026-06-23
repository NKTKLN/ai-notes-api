"""Document storage module.

This module provides a storage helper for uploading, downloading, and deleting
documents in S3 object storage.
"""

from typing import Any
from uuid import UUID

from botocore.exceptions import ClientError
from loguru import logger

from ai_notes_api.core import settings


class DocumentStorage:
    """Object storage helper for documents.

    Args:
        client (Any): Asynchronous S3 client used to perform object storage operations.
    """

    def __init__(self, client: Any) -> None:
        """Initialize the document storage helper.

        Args:
            client (Any): Asynchronous S3 client used to perform object storage
                operations.
        """
        self.client = client
        self.bucket = settings.s3_bucket_name

    async def ensure_bucket(self) -> None:
        """Create the storage bucket if it does not already exist."""
        try:
            await self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            await self.client.create_bucket(Bucket=self.bucket)
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

    async def upload_file(
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
        await self.ensure_bucket()

        object_name = self.build_object_name(
            user_id=user_id,
            document_id=document_id,
            filename=filename,
        )

        await self.client.put_object(
            Bucket=self.bucket,
            Key=object_name,
            Body=data,
            ContentType=content_type,
        )

        logger.info(
            "Document uploaded: object_name={}, size={}",
            object_name,
            len(data),
        )

        return object_name

    async def download_file(self, object_name: str) -> bytes:
        """Download a document from object storage.

        Args:
            object_name (str): Object name within the storage bucket.

        Returns:
            bytes: Raw document content.
        """
        response = await self.client.get_object(
            Bucket=self.bucket,
            Key=object_name,
        )

        body = response["Body"]

        try:
            data: bytes = await body.read()
        finally:
            body.close()

        logger.debug("Document downloaded: object_name={}", object_name)

        return data

    async def get_presigned_download_url(
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
            expires_in_seconds = settings.s3_presigned_url_expire_seconds

        url: str = await self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_name},
            ExpiresIn=expires_in_seconds,
        )

        logger.debug(
            "Presigned download URL created: object_name={}, expires_in_seconds={}",
            object_name,
            expires_in_seconds,
        )

        return url

    async def delete_file(self, object_name: str) -> None:
        """Delete a document from object storage.

        Args:
            object_name (str): Object name within the storage bucket.
        """
        await self.client.delete_object(Bucket=self.bucket, Key=object_name)

        logger.info("Document deleted: object_name={}", object_name)
