"""Text extraction module.

This module provides :class:`TextExtractor`, which converts raw document bytes
of various formats into markdown text using MarkItDown.
"""

import asyncio
from io import BytesIO

from loguru import logger
from markitdown import MarkItDown, StreamInfo, UnsupportedFormatException

from ai_notes_api.exceptions import UnsupportedDocumentFormatError


class TextExtractor:
    """Extracts markdown text from raw document bytes.

    Conversion is delegated to MarkItDown and runs in a thread pool executor so
    that the synchronous extraction does not block the event loop.
    """

    async def extract(self, data: bytes, content_type: str) -> str:
        """Extract markdown text from raw document bytes.

        Args:
            data (bytes): Raw document content to convert.
            content_type (str): MIME type of the document.

        Returns:
            str: Extracted document text as markdown.

        Raises:
            UnsupportedDocumentFormatError: If MarkItDown does not support the
                given content type.
        """
        logger.debug(
            "Extracting text: content_type={}, size={} bytes",
            content_type,
            len(data),
        )

        def _convert() -> str:
            md = MarkItDown()

            try:
                result = md.convert_stream(
                    BytesIO(data),
                    stream_info=StreamInfo(mimetype=content_type),
                )

            except UnsupportedFormatException as exc:
                logger.warning(
                    "Unsupported document format: content_type={}", content_type
                )
                raise UnsupportedDocumentFormatError(content_type) from exc

            return result.markdown

        loop = asyncio.get_running_loop()
        markdown = await loop.run_in_executor(None, _convert)

        logger.debug(
            "Text extraction finished: content_type={}, chars={}",
            content_type,
            len(markdown),
        )

        return markdown
