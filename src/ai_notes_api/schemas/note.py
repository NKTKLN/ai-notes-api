"""Note schemas module.

This module defines Pydantic schemas used for note request and response validation.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from ai_notes_api.db.models import ModelSource

Tag = Annotated[
    str,
    Field(
        min_length=1,
        max_length=50,
    ),
]


class NoteResponseSchema(BaseModel):
    """Schema for returning a note.

    Attributes:
        id (int): Unique note identifier.
        title (str): Note title.
        content (str): Main note content.
        tags (list[str]): List of note tags.
        source (ModelSource): Source that indicates how the note was created.
        model_name (str | None): Optional name of the model associated with the note.
        model_metadata (dict[str, Any] | None): Additional metadata associated
            with the note.
        created_at (datetime): Date and time when the note was created.
        updated_at (datetime): Date and time when the note was last updated.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int
    title: str
    content: str
    tags: list[str]
    source: ModelSource
    model_name: str | None
    model_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class NoteListResponseSchema(BaseModel):
    """Schema for returning a paginated list of notes.

    Attributes:
        items (list[NoteResponseSchema]): List of note response items.
        limit (int): Maximum number of notes requested.
        offset (int): Number of notes skipped before returning results.
        total (int): Total number of matching notes.
    """

    items: list[NoteResponseSchema]
    limit: int
    offset: int
    total: int


class NoteCreateSchema(BaseModel):
    """Schema for creating a note.

    Attributes:
        title (str): Note title.
        content (str): Main note content.
        tags (list[Tag]): List of note tags.
        source (ModelSource): Source that indicates how the note was created.
        model_name (str | None): Optional name of the model associated with the note.
        model_metadata (dict[str, Any]): Additional metadata associated with the note.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    content: str = Field(
        default_factory=str,
    )

    tags: list[Tag] = Field(
        max_length=20,
        default_factory=list,
    )

    source: ModelSource = Field(
        default=ModelSource.MANUAL,
    )

    model_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    model_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class NoteListQuerySchema(BaseModel):
    """Filters and pagination parameters for listing notes.

    Attributes:
        limit (int): Maximum number of notes to return.
        offset (int): Number of notes to skip before returning results.
        search (str | None): Optional text used to search notes by title or content.
        source (ModelSource | None): Optional note source used to filter results.
        tag (str | None): Optional tag used to filter results.
        model_name (str | None): Optional model name used to filter results.
    """

    limit: int = Query(default=20, ge=1, le=100)
    offset: int = Query(default=0, ge=0)
    search: str | None = None
    source: ModelSource | None = None
    tag: str | None = None
    model_name: str | None = None


class NoteUpdateSchema(BaseModel):
    """Schema for updating a note.

    Attributes:
        title (str | None): Optional note title.
        content (str | None): Optional main note content.
        tags (list[str] | None): Optional list of note tags.
        source (ModelSource | None): Optional source that indicates how the note
            was created.
        model_name (str | None): Optional name of the model associated with the note.
        model_metadata (dict[str, Any] | None): Optional metadata associated
            with the note.
    """

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    content: str | None = Field(
        default=None,
    )

    tags: list[str] | None = Field(
        default=None,
        max_length=20,
    )

    source: ModelSource | None = None

    model_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )

    model_metadata: dict[str, Any] | None = None
