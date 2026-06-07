"""Note schemas module.

This module defines Pydantic schemas used for note request and response validation.
"""

from datetime import datetime
from typing import Annotated, Any

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
        id: Unique note identifier.
        title: Note title.
        content: Main note content.
        tags: List of note tags.
        source: Source that indicates how the note was created.
        model_name: Optional name of the model associated with the note.
        model_metadata: Additional metadata associated with the note.
        created_at: Date and time when the note was created.
        updated_at: Date and time when the note was last updated.
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


class NoteCreateSchema(BaseModel):
    """Schema for creating a note.

    Attributes:
        title: Note title.
        content: Main note content.
        tags: List of note tags.
        source: Source that indicates how the note was created.
        model_name: Optional name of the model associated with the note.
        model_metadata: Additional metadata associated with the note.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    content: str = Field(
        min_length=1,
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
