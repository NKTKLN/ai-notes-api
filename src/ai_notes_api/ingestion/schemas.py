"""Ingestion data models module.

This module defines dataclasses representing artifacts produced while ingesting
documents, such as text chunks.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """Chunk of text extracted from a document during ingestion.

    Attributes:
        index (int): Zero-based position of the chunk within the document.
        content (str): Text content of the chunk.
        content_hash (str): Hash of the content used for deduplication.
        token_count (int | None): Number of tokens in the chunk, if known.
    """

    index: int
    content: str
    content_hash: str
    token_count: int | None = None
