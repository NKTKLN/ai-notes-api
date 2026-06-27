"""Repositories package.

This package re-exports repository classes used for database access.
"""

from ai_notes_api.repositories.base import BaseRepository
from ai_notes_api.repositories.chat_memory import ChatMemoryRepository
from ai_notes_api.repositories.chat_session import ChatSessionRepository
from ai_notes_api.repositories.document import DocumentRepository
from ai_notes_api.repositories.document_chunk import DocumentChunkRepository
from ai_notes_api.repositories.document_processing_job import (
    DocumentProcessingJobRepository,
)
from ai_notes_api.repositories.filters import (
    ChatSessionListFilters,
    GenerationJobListFilters,
    MessageListFilters,
    NoteListFilters,
)
from ai_notes_api.repositories.generation_job import GenerationJobRepository
from ai_notes_api.repositories.message import MessageRepository
from ai_notes_api.repositories.note import NoteRepository
from ai_notes_api.repositories.user import UserRepository

__all__ = [
    "BaseRepository",
    "ChatSessionListFilters",
    "ChatSessionRepository",
    "GenerationJobListFilters",
    "GenerationJobRepository",
    "MessageListFilters",
    "MessageRepository",
    "NoteListFilters",
    "NoteRepository",
    "UserRepository",
    "ChatMemoryRepository",
    "DocumentRepository",
    "DocumentChunkRepository",
    "DocumentProcessingJobRepository",
]
