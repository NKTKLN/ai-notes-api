"""Notes API router.

This module defines API endpoints for creating and managing notes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_note_service
from ai_notes_api.schemas.note import NoteCreateSchema, NoteResponseSchema
from ai_notes_api.services.note import NoteService

router = APIRouter(
    prefix="/notes",
    tags=["Notes"],
)


@router.post(
    "",
    summary="Create a new note",
    description="Create a new note and return the created note data.",
    response_model=NoteResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    data: NoteCreateSchema,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteResponseSchema:
    """Create a new note.

    Args:
        data: Validated note creation data.
        service: Note service dependency used to create the note.

    Returns:
        NoteResponseSchema: Created note data.
    """
    logger.info("Note creation requested")

    note = await service.create_note(data)

    return NoteResponseSchema.model_validate(note)
