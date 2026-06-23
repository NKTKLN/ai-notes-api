"""Database models package.

This package re-exports the base class used by SQLAlchemy ORM models.
"""

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.chat_memory import ChatMemory
from ai_notes_api.db.models.chat_session import ChatSession, ChatSessionGenerationStatus
from ai_notes_api.db.models.datetime import SoftDeleteMixin, TimestampMixin
from ai_notes_api.db.models.document import Document, DocumentStatus
from ai_notes_api.db.models.document_chunk import DocumentChunk
from ai_notes_api.db.models.generation_job import GenerationJob, GenerationJobStatus
from ai_notes_api.db.models.message import Message, MessageRole
from ai_notes_api.db.models.note import ModelSource, Note
from ai_notes_api.db.models.rag_query import RagQuery, RagQueryStatus
from ai_notes_api.db.models.rag_query_source import RagQuerySource
from ai_notes_api.db.models.user import User

__all__ = [
    "Base",
    "ChatSession",
    "Message",
    "MessageRole",
    "ModelSource",
    "Note",
    "SoftDeleteMixin",
    "TimestampMixin",
    "User",
    "GenerationJob",
    "GenerationJobStatus",
    "ChatSessionGenerationStatus",
    "ChatMemory",
    "Document",
    "DocumentStatus",
    "DocumentChunk",
    "RagQuery",
    "RagQueryStatus",
    "RagQuerySource",
]
