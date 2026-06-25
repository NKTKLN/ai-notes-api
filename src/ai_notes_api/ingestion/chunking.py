"""Text chunking module.

This module provides :class:`TokenTextChunker`, which splits extracted text into
token-based overlapping chunks suitable for embedding.
"""

import asyncio
import hashlib

import tiktoken
from loguru import logger

from ai_notes_api.core import settings
from ai_notes_api.exceptions import (
    InvalidChunkSizeError,
    InvalidOverlapError,
    OverlapGreaterThanOrEqualChunkSizeError,
)
from ai_notes_api.ingestion.schemas import TextChunk


class TokenTextChunker:
    """Splits text into token-based overlapping chunks.

    Text is tokenized with the configured tiktoken encoding and split into
    fixed-size windows that overlap by a configurable number of tokens.
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200) -> None:
        """Initialize the chunker and validate its configuration.

        Args:
            chunk_size (int): Maximum number of tokens in each chunk.
            overlap (int): Number of tokens repeated between adjacent chunks.

        Raises:
            InvalidChunkSizeError: If `chunk_size` is less than or equal to zero.
            InvalidOverlapError: If `overlap` is negative.
            OverlapGreaterThanOrEqualChunkSizeError: If `overlap` is greater than
                or equal to `chunk_size`.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding_name = settings.tiktoken_encoding_name

        if chunk_size <= 0:
            raise InvalidChunkSizeError()

        if overlap < 0:
            raise InvalidOverlapError()

        if overlap >= chunk_size:
            raise OverlapGreaterThanOrEqualChunkSizeError()

    async def chunk(self, text: str) -> list[TextChunk]:
        """Split extracted text into token-based overlapping chunks.

        Args:
            text (str): Plain text to split.

        Returns:
            list[TextChunk]: Ordered non-empty text chunks ready for embedding.
        """
        logger.debug(
            "Chunking text: chars={}, chunk_size={}, overlap={}",
            len(text),
            self.chunk_size,
            self.overlap,
        )

        def _chunk() -> list[TextChunk]:
            encoding = tiktoken.get_encoding(self.encoding_name)

            tokens = encoding.encode(text)
            chunks = []

            step = self.chunk_size - self.overlap

            for start in range(0, len(tokens), step):
                end = start + self.chunk_size
                chunk_tokens = tokens[start:end]

                content = encoding.decode(chunk_tokens).strip()

                if content:
                    chunks.append(
                        TextChunk(
                            index=len(chunks),
                            content=content,
                            content_hash=hashlib.sha256(
                                content.encode("utf-8")
                            ).hexdigest(),
                            token_count=len(chunk_tokens),
                        )
                    )

                if end >= len(tokens):
                    break

            return chunks

        loop = asyncio.get_running_loop()
        chunks = await loop.run_in_executor(None, _chunk)

        logger.debug("Chunking finished: chunks={}", len(chunks))

        return chunks
