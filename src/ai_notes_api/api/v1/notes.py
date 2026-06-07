"""Notes API router.

This module defines API endpoints for creating and managing notes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_note_service
from ai_notes_api.schemas import (
    ErrorResponseSchema,
    NoteCreateSchema,
    NoteResponseSchema,
)
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
        data (NoteCreateSchema): Validated note creation data.
        service (NoteService): Note service dependency used to create the note.

    Returns:
        NoteResponseSchema: Created note data.
    """
    logger.info("Note creation requested")

    note = await service.create_note(data)

    return NoteResponseSchema.model_validate(note)


@router.get(
    "/{note_id}",
    summary="Get note by ID",
    description="Return a note by its unique identifier.",
    response_model=NoteResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Note not found",
        },
    },
)
async def get_note(
    note_id: int,
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteResponseSchema:
    """Return a note by its identifier.

    Args:
        note_id (int): Unique note identifier.
        service (NoteService): Note service dependency used to retrieve the note.

    Returns:
        NoteResponseSchema: Note data.

    Raises:
        NoteNotFoundError: If no note with the given identifier exists.
    """
    logger.info(f"Note retrieval requested: note_id={note_id}")

    note = await service.get_note(note_id)

    return NoteResponseSchema.model_validate(note)
