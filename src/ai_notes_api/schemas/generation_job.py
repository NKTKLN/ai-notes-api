"""Generation job schemas module.

This module defines Pydantic schemas used for generation job API requests and
responses.
"""

from datetime import datetime
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import GenerationJobStatus


class GenerationJobCreateSchema(BaseModel):
    """Schema for creating a generation job.

    Attributes:
        session_id (UUID): Unique chat session identifier.
        message (str): User input message used for generation.
    """

    session_id: UUID
    message: str = Field(min_length=1, max_length=10_000)


class GenerationJobResponseSchema(BaseModel):
    """Schema for returning generation job data.

    Attributes:
        id (UUID): Unique generation job identifier.
        session_id (UUID): Unique chat session identifier.
        status (GenerationJobStatus): Current generation job status.
        input_message (str): User input message used for generation.
        output_message_id (UUID | None): Optional identifier of the generated
            assistant message.
        error (str | None): Optional error message if generation failed.
        created_at (datetime): Date and time when the generation job was created.
        started_at (datetime | None): Date and time when generation started.
        finished_at (datetime | None): Date and time when generation finished.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    status: GenerationJobStatus
    input_message: str
    output_message_id: UUID | None = None
    error: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GenerationJobUpdateSchema(BaseModel):
    """Schema for updating a generation job.

    Attributes:
        status (GenerationJobStatus | None): Optional generation job status.
        output_message_id (UUID | None): Optional identifier of the generated
            assistant message.
        error (str | None): Optional error message if generation failed.
        started_at (datetime | None): Optional date and time when generation
            started.
        finished_at (datetime | None): Optional date and time when generation
            finished.
    """

    status: GenerationJobStatus | None = None
    output_message_id: UUID | None = None

    error: str | None = Field(
        default=None,
        max_length=10_000,
    )

    started_at: datetime | None = None
    finished_at: datetime | None = None


class GenerationJobListResponseSchema(BaseModel):
    """Schema for returning a paginated list of generation jobs.

    Attributes:
        items (list[GenerationJobResponseSchema]): List of generation jobs.
        limit (int): Maximum number of generation jobs returned.
        offset (int): Number of generation jobs skipped before returning results.
        total (int): Total number of generation jobs in the current page.
    """

    items: list[GenerationJobResponseSchema]
    limit: int
    offset: int
    total: int


class GenerationJobListQuerySchema(BaseModel):
    """Schema for generation job list query parameters.

    Attributes:
        limit (int): Maximum number of generation jobs to return.
        offset (int): Number of generation jobs to skip before returning results.
        search (str | None): Optional text used to search input messages.
        status (GenerationJobStatus | None): Optional generation job status used
            to filter results.
    """

    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)
    search: str | None = None
    status: GenerationJobStatus | None = None
