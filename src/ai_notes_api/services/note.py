"""Note service module.

This module provides business logic for working with notes.
"""

from uuid import UUID

from ai_notes_api.db.models import Note
from ai_notes_api.exceptions import NoteNotFoundError
from ai_notes_api.repositories import NoteListFilters, NoteRepository
from ai_notes_api.schemas import NoteCreateSchema, NoteListQuerySchema, NoteUpdateSchema


class NoteService:
    """Service for note-related business operations.

    Args:
        repository (NoteRepository): Repository used to perform note
            database operations.
    """

    def __init__(self, repository: NoteRepository) -> None:
        """Initialize the note service.

        Args:
            repository (NoteRepository): Note repository used by the service.
        """
        self.repository = repository

    async def create_note(self, user_id: UUID, data: NoteCreateSchema) -> Note:
        """Create a note.

        Args:
            user_id (UUID): Unique identifier of the user creating the note.
            data (NoteCreateSchema): Validated data used to create the note.

        Returns:
            Note: Created note instance.
        """
        note = Note(
            user_id=user_id,
            title=data.title,
            content=data.content,
            tags=data.tags,
            source=data.source,
            model_name=data.model_name,
            model_metadata=data.model_metadata,
        )

        return await self.repository.create(note)

    async def get_notes_list(
        self, user_id: UUID, filters: NoteListQuerySchema
    ) -> list[Note]:
        """Return a list of notes matching the given filters.

        Args:
            user_id (UUID): Unique identifier of the user whose notes are requested.
            filters (NoteListQuerySchema): API filters and pagination parameters.

        Returns:
            list[Note]: List of matching notes.
        """
        repository_filters = NoteListFilters(
            search=filters.search,
            source=filters.source,
            tag=filters.tag,
            model_name=filters.model_name,
            limit=filters.limit,
            offset=filters.offset,
        )

        return await self.repository.get_list(user_id, repository_filters)

    async def get_note(self, user_id: UUID, note_id: UUID) -> Note:
        """Return a note by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the note.
            note_id (UUID): Unique note identifier.

        Returns:
            Note: Matching note.

        Raises:
            NoteNotFoundError: If no note with the given identifier exists.
        """
        note = await self.repository.get_by_id(user_id, note_id)

        if note is None:
            raise NoteNotFoundError()

        return note

    async def update_note(
        self,
        user_id: UUID,
        note_id: UUID,
        note_update: NoteUpdateSchema,
    ) -> Note:
        """Update a note by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the note.
            note_id (UUID): Unique note identifier.
            note_update (NoteUpdateSchema): Validated note update data.

        Returns:
            Note: Updated note.

        Raises:
            NoteNotFoundError: If no note with the given identifier exists.
        """
        note = await self.repository.get_by_id(user_id, note_id)

        if note is None:
            raise NoteNotFoundError()

        update_data = note_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(note, field, value)

        await self.repository.update(note)

        return note

    async def delete_note(self, user_id: UUID, note_id: UUID) -> None:
        """Delete a note by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the note.
            note_id (UUID): Unique note identifier to delete.

        Raises:
            NoteNotFoundError: If no note with the given identifier exists.
        """
        note = await self.repository.get_by_id(user_id, note_id)

        if note is None:
            raise NoteNotFoundError()

        await self.repository.soft_delete(note)
