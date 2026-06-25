"""Document ingestion package.

This package provides the building blocks that turn a raw uploaded document into
embeddable text: extracting text from binary document formats and splitting that
text into token-based overlapping chunks.
"""

from ai_notes_api.ingestion.chunking import TokenTextChunker
from ai_notes_api.ingestion.schemas import TextChunk
from ai_notes_api.ingestion.text_extractor import TextExtractor

__all__ = ["TextExtractor", "TokenTextChunker", "TextChunk"]
