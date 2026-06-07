"""Note service module.

This module provides business logic for working with notes.
"""

from ai_notes_api.db.models import Note
from ai_notes_api.repositories import NoteRepository
from ai_notes_api.schemas import NoteCreateSchema


class NoteService:
    """Service for note-related business operations.

    Args:
        repository: Repository used to perform note database operations.
    """

    def __init__(self, repository: NoteRepository) -> None:
        """Initialize the note service.

        Args:
            repository: Note repository used by the service.
        """
        self.repository = repository

    async def create_note(self, data: NoteCreateSchema) -> Note:
        """Create a note.

        Args:
            data: Validated data used to create the note.

        Returns:
            Note: Created note instance.
        """
        note = Note(
            title=data.title,
            content=data.content,
            tags=data.tags,
            source=data.source,
            model_name=data.model_name,
            model_metadata=data.model_metadata,
        )

        return await self.repository.create(note)

    async def get_note(self, note_id: int) -> Note | None:
        """Return a note by its identifier.

        Args:
            note_id: Unique note identifier.

        Returns:
            Note | None: Matching note if found; otherwise, None.
        """
        return await self.repository.get_by_id(note_id)
