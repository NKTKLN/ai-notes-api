"""Tests for the RAG prompt builder."""

from uuid import UUID

from ai_notes_api.db.models import DocumentChunk
from ai_notes_api.rag.prompt_builder import RAGPromptBuilder

TEST_DOCUMENT_ID = UUID("44444444-4444-4444-4444-444444444444")
TEST_CHUNK_ID = UUID("55555555-5555-5555-5555-555555555555")


def _chunk(content: str, chunk_id: UUID = TEST_CHUNK_ID) -> DocumentChunk:
    """Return a document chunk with the given content for prompt builder tests."""
    return DocumentChunk(
        id=chunk_id,
        document_id=TEST_DOCUMENT_ID,
        content=content,
    )


def test_build_returns_context_then_question() -> None:
    """Test that the prompt is a trusted context message followed by the question."""
    messages = RAGPromptBuilder.build(
        question="What is RAG?",
        chunks=[_chunk("Retrieval augmented generation.")],
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert "Retrieval augmented generation." in messages[0]["content"]
    assert "<chunks>" in messages[0]["content"]

    assert messages[1] == {"role": "user", "content": "What is RAG?"}


def test_build_indexes_and_attributes_chunks() -> None:
    """Test that chunks are numbered and labeled with their document id."""
    messages = RAGPromptBuilder.build(
        question="Question",
        chunks=[_chunk("First"), _chunk("Second")],
    )

    content = messages[0]["content"]
    assert "[1]" in content
    assert "[2]" in content
    assert str(TEST_DOCUMENT_ID) in content


def test_build_strips_chunk_content() -> None:
    """Test that surrounding whitespace is stripped from chunk content."""
    messages = RAGPromptBuilder.build(
        question="Question",
        chunks=[_chunk("  padded content  ")],
    )

    assert "padded content" in messages[0]["content"]
    assert "  padded content  " not in messages[0]["content"]


def test_build_without_chunks_uses_placeholder() -> None:
    """Test that an empty chunk list renders the no-chunks placeholder."""
    messages = RAGPromptBuilder.build(question="Question", chunks=[])

    assert "No relevant chunks found." in messages[0]["content"]
    assert messages[1]["content"] == "Question"
