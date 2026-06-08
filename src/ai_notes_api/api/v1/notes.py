"""Notes API router.

This module defines API endpoints for creating and managing notes.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger

from ai_notes_api.api.v1.dependencies import get_current_user_id, get_note_service
from ai_notes_api.schemas import (
    ErrorResponseSchema,
    NoteCreateSchema,
    NoteListQuerySchema,
    NoteListResponseSchema,
    NoteResponseSchema,
    NoteUpdateSchema,
    StatusResponseSchema,
)
from ai_notes_api.services import NoteService

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
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteResponseSchema:
    """Create a new note.

    Args:
        data (NoteCreateSchema): Validated note creation data.
        user_id (int): Current authenticated user identifier.
        service (NoteService): Note service dependency used to create the note.

    Returns:
        NoteResponseSchema: Created note data.
    """
    logger.info("Note creation requested")

    note = await service.create_note(user_id, data)

    return NoteResponseSchema.model_validate(note)


@router.get(
    "",
    summary="Get notes",
    description="Return a paginated list of notes.",
    response_model=NoteListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_notes(
    filters: Annotated[
        NoteListQuerySchema,
        Depends(),
    ],
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteListResponseSchema:
    """Return a paginated list of notes.

    Args:
        filters (NoteListQuerySchema): Filters and pagination parameters.
        user_id (int): Current authenticated user identifier.
        service (NoteService): Note service dependency used to retrieve notes.

    Returns:
        NoteListResponseSchema: Paginated list of notes.
    """
    logger.info(
        (
            "Notes list retrieval requested: limit={}, offset={}, search={}, "
            "source={}, tag={}, model_name={}"
        ),
        filters.limit,
        filters.offset,
        filters.search,
        filters.source,
        filters.tag,
        filters.model_name,
    )

    notes = await service.get_list(user_id, filters)

    return NoteListResponseSchema(
        items=[NoteResponseSchema.model_validate(note) for note in notes],
        limit=filters.limit,
        offset=filters.offset,
        total=len(notes),
    )


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
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteResponseSchema:
    """Return a note by its identifier.

    Args:
        note_id (int): Unique note identifier.
        user_id (int): Current authenticated user identifier.
        service (NoteService): Note service dependency used to retrieve the note.

    Returns:
        NoteResponseSchema: Note data.

    Raises:
        NoteNotFoundError: If no note with the given identifier exists.
    """
    logger.info("Note retrieval requested: note_id={}", note_id)

    note = await service.get_note(user_id, note_id)

    return NoteResponseSchema.model_validate(note)


@router.patch(
    "/{note_id}",
    summary="Update note by ID",
    description="Update a note by its unique identifier.",
    response_model=NoteResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Note not found",
        },
    },
)
async def update_note(
    note_id: int,
    data: NoteUpdateSchema,
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> NoteResponseSchema:
    """Update a note by its identifier.

    Args:
        note_id (int): Unique note identifier to update.
        data (NoteUpdateSchema): Validated note update data.
        user_id (int): Current authenticated user identifier.
        service (NoteService): Note service dependency used to update the note.

    Returns:
        NoteResponseSchema: Updated note data.

    Raises:
        NoteNotFoundError: If no note with the given identifier exists.
    """
    logger.info("Note update requested: note_id={}", note_id)

    note = await service.update_note(user_id, note_id, data)

    return NoteResponseSchema.model_validate(note)


@router.delete(
    "/{note_id}",
    summary="Delete note by ID",
    description="Delete a note by its unique identifier.",
    response_model=StatusResponseSchema,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "model": ErrorResponseSchema,
            "description": "Note not found",
        },
    },
)
async def delete_note(
    note_id: int,
    user_id: Annotated[int, Depends(get_current_user_id)],
    service: Annotated[NoteService, Depends(get_note_service)],
) -> StatusResponseSchema:
    """Delete a note by its identifier.

    Args:
        note_id (int): Unique note identifier to delete.
        user_id (int): Current authenticated user identifier.
        service (NoteService): Note service dependency used to delete the note.

    Returns:
        StatusResponseSchema: Response status.

    Raises:
        NoteNotFoundError: If no note with the given identifier exists.
    """
    logger.info("Note deletion requested: note_id={}", note_id)

    await service.delete_note(user_id, note_id)

    return StatusResponseSchema(status="deleted")
