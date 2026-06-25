"""S3 client module.

This module defines an asynchronous S3 client factory configured from
application settings.
"""

from collections.abc import AsyncIterator
from typing import Any

import aioboto3
from botocore.config import Config

from ai_notes_api.core import settings


async def get_s3_client() -> AsyncIterator[Any]:
    """Yield a configured asynchronous S3 client.

    Yields:
        Any: Asynchronous S3 client bound to the configured endpoint and credentials.
    """
    session = aioboto3.Session()

    async with session.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    ) as s3:
        yield s3
