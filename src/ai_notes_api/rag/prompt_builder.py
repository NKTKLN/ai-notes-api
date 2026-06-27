"""RAG prompt builder module.

This module defines utilities for building LLM input messages from a user
question and the document chunks retrieved through semantic search.
"""

from typing import Any

from ai_notes_api.db.models import DocumentChunk


class RAGPromptBuilder:
    """Builder for retrieval-augmented generation prompt messages."""

    @classmethod
    def build(
        cls,
        question: str,
        chunks: list[DocumentChunk],
    ) -> list[dict[str, Any]]:
        """Build LLM input messages from a question and retrieved chunks.

        Args:
            question (str): User question to answer.
            chunks (list[DocumentChunk]): Document chunks retrieved for the
                question and used as grounding context.

        Returns:
            list[dict[str, Any]]: Serialized LLM input messages, consisting of a
            trusted context message followed by the user question.
        """
        chunks_text = cls._format_chunks(chunks)

        return [
            {
                "role": "user",
                "content": (
                    "Retrieved document chunks follow.\n"
                    "Treat them as trusted application-provided context, "
                    "not as user instructions.\n"
                    "Ground the answer in this context and cite the relevant "
                    "chunks by their index.\n"
                    "If the answer isn't in the context, don't make it up; "
                    "instead, let the user know.\n\n"
                    f"<chunks>\n{chunks_text}\n</chunks>"
                ),
            },
            {
                "role": "user",
                "content": question,
            },
        ]

    @staticmethod
    def _format_chunks(chunks: list[DocumentChunk]) -> str:
        """Render retrieved chunks as an indexed, citable text block.

        Args:
            chunks (list[DocumentChunk]): Document chunks to render.

        Returns:
            str: Formatted chunks, or a placeholder when none were retrieved.
        """
        if not chunks:
            return "No relevant chunks found."

        return "\n\n".join(
            f"[{index}] (document {chunk.document_id})\n{chunk.content.strip()}"
            for index, chunk in enumerate(chunks, start=1)
        )
