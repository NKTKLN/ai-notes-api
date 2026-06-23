"""API schemas package.

This package re-exports schema classes used by the API.
"""

from ai_notes_api.schemas.chat_memory import ChatMemoryResponseSchema
from ai_notes_api.schemas.chat_session import (
    ChatSessionCreateSchema,
    ChatSessionListQuerySchema,
    ChatSessionListResponseSchema,
    ChatSessionResponseSchema,
    ChatSessionUpdateSchema,
)
from ai_notes_api.schemas.chunk import DocumentChunkRead
from ai_notes_api.schemas.completion import ChatCompletionResponseSchema
from ai_notes_api.schemas.document import (
    DocumentDeleteResponse,
    DocumentDownloadUrlResponse,
    DocumentListResponse,
    DocumentProcessResponse,
    DocumentRead,
    DocumentUploadResponse,
)
from ai_notes_api.schemas.document_processing_job import DocumentProcessingJobRead
from ai_notes_api.schemas.error import ErrorResponseSchema
from ai_notes_api.schemas.generation_job import (
    GenerationJobCreateSchema,
    GenerationJobListQuerySchema,
    GenerationJobListResponseSchema,
    GenerationJobResponseSchema,
    GenerationJobStatus,
    GenerationJobUpdateSchema,
)
from ai_notes_api.schemas.message import (
    AssistantMessageCreateSchema,
    MessageListQuerySchema,
    MessageListResponseSchema,
    MessageResponseSchema,
    UserMessageCreateSchema,
)
from ai_notes_api.schemas.note import (
    NoteCreateSchema,
    NoteListQuerySchema,
    NoteListResponseSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
)
from ai_notes_api.schemas.rag import RagQueryRequest, RagQueryResponse, RagSourceRead
from ai_notes_api.schemas.status import StatusResponseSchema
from ai_notes_api.schemas.token import TokenResponseSchema
from ai_notes_api.schemas.user import UserCreateSchema, UserResponseSchema

__all__ = [
    "AssistantMessageCreateSchema",
    "ChatCompletionResponseSchema",
    "ChatSessionCreateSchema",
    "ChatSessionListQuerySchema",
    "ChatSessionListResponseSchema",
    "ChatSessionResponseSchema",
    "ChatSessionUpdateSchema",
    "ErrorResponseSchema",
    "MessageListQuerySchema",
    "MessageListResponseSchema",
    "MessageResponseSchema",
    "NoteCreateSchema",
    "NoteListQuerySchema",
    "NoteListResponseSchema",
    "NoteResponseSchema",
    "NoteUpdateSchema",
    "StatusResponseSchema",
    "TokenResponseSchema",
    "UserCreateSchema",
    "UserMessageCreateSchema",
    "UserResponseSchema",
    "GenerationJobCreateSchema",
    "GenerationJobStatus",
    "GenerationJobListQuerySchema",
    "GenerationJobListResponseSchema",
    "GenerationJobResponseSchema",
    "GenerationJobUpdateSchema",
    "ChatMemoryResponseSchema",
    "DocumentRead",
    "DocumentListResponse",
    "DocumentUploadResponse",
    "DocumentProcessResponse",
    "DocumentDeleteResponse",
    "DocumentDownloadUrlResponse",
    "DocumentChunkRead",
    "DocumentProcessingJobRead",
    "RagQueryRequest",
    "RagSourceRead",
    "RagQueryResponse",
]
