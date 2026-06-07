"""Tests for note service."""

from datetime import UTC, datetime
from typing import cast

import pytest

from ai_notes_api.db.models import ModelSource, Note
from ai_notes_api.exceptions import NoteNotFoundError
from ai_notes_api.repositories import NoteListFilters
from ai_notes_api.repositories.note import NoteRepository
from ai_notes_api.schemas import NoteCreateSchema, NoteListQuerySchema, NoteUpdateSchema
from ai_notes_api.services import NoteService


class FakeNoteRepository:
    """Fake note repository used for testing note service behavior.

    Attributes:
        notes (dict[int, Note]): In-memory storage of notes by identifier.
        created_note (Note | None): Last note created through the fake repository.
    """

    def __init__(self) -> None:
        """Initialize the fake note repository."""
        self.notes: dict[int, Note] = {}
        self.created_note: Note | None = None

    async def create(self, note: Note) -> Note:
        """Create a note in the fake repository.

        Args:
            note (Note): Note instance to create.

        Returns:
            Note: Created note with assigned identifier.
        """
        note.id = 1
        self.created_note = note
        self.notes[note.id] = note
        return note

    async def get_by_id(self, note_id: int) -> Note | None:
        """Return a note by its identifier.

        Args:
            note_id (int): Unique note identifier.

        Returns:
            Note | None: Matching note if found; otherwise, None.
        """
        return self.notes.get(note_id)

    async def get_list(self, filters: NoteListFilters) -> list[Note]:
        """Return notes matching the provided filters.

        Args:
            filters (NoteListFilters): Filters and pagination parameters.

        Returns:
            list[Note]: List of matching non-deleted notes.
        """
        notes = [note for note in self.notes.values() if note.deleted_at is None]

        if filters.source is not None:
            notes = [note for note in notes if note.source == filters.source]

        if filters.tag is not None:
            notes = [note for note in notes if filters.tag in note.tags]

        if filters.model_name is not None:
            notes = [note for note in notes if note.model_name == filters.model_name]

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                notes = [
                    note
                    for note in notes
                    if search in note.title.strip() or search in note.content.strip()
                ]

        return notes[filters.offset : filters.offset + filters.limit]

    async def update(self, note: Note) -> Note:
        """Update a note in the fake repository.

        Args:
            note (Note): Note instance with updated values.

        Returns:
            Note: Updated note.
        """
        self.notes[note.id] = note
        return note

    async def soft_delete(self, note: Note) -> None:
        """Soft-delete a note in the fake repository.

        Args:
            note (Note): Note instance to soft-delete.

        Raises:
            NoteNotFoundError: If no note with the given identifier exists.

        Returns:
            None.
        """
        stored_note = self.notes.get(note.id)

        if stored_note is None:
            raise NoteNotFoundError()

        stored_note.deleted_at = datetime.now(UTC)


@pytest.mark.asyncio
async def test_create_note_success() -> None:
    """Test successful note creation."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    data = NoteCreateSchema(
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    note = await service.create_note(data)

    assert note.id == 1
    assert note.title == "Test"
    assert note.content == "Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_get_note_success() -> None:
    """Test successful note retrieval by identifier."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[1] = Note(
        id=1,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    note = await service.get_note(1)

    assert note is not None
    assert note.title == "Test"


@pytest.mark.asyncio
async def test_get_note_not_found() -> None:
    """Test that note retrieval raises an error when the note is not found."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    with pytest.raises(NoteNotFoundError):
        await service.get_note(999)


@pytest.mark.asyncio
async def test_update_note_success() -> None:
    """Test successful note update."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[1] = Note(
        id=1,
        title="Old Test",
        content="Old Content",
        tags=[],
        source=ModelSource.MANUAL,
    )

    data = NoteUpdateSchema(
        title="New Test",
        content="New Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    note = await service.update_note(1, data)

    assert note.title == "New Test"
    assert note.content == "New Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_update_note_not_found() -> None:
    """Test that note update raises an error when the note is not found."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    data = NoteUpdateSchema(
        title="New Test",
        content="New Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    with pytest.raises(NoteNotFoundError):
        await service.update_note(999, data)


@pytest.mark.asyncio
async def test_delete_note_success() -> None:
    """Test successful note deletion."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[1] = Note(
        id=1,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    await service.delete_note(1)

    assert repository.notes[1].deleted_at is not None


@pytest.mark.asyncio
async def test_delete_note_not_found() -> None:
    """Test that note deletion raises an error when the note is not found."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    with pytest.raises(NoteNotFoundError):
        await service.delete_note(999)


@pytest.mark.asyncio
async def test_get_notes_list_success() -> None:
    """Test successful notes list retrieval with filters."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[1] = Note(
        id=1,
        title="First Test",
        content="First Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    repository.notes[2] = Note(
        id=2,
        title="Second Test",
        content="Second Content",
        tags=[],
        source=ModelSource.API,
    )

    data = NoteListQuerySchema(
        limit=1,
        search="Test",
        source=ModelSource.MANUAL,
        tag="fastapi",
    )

    notes = await service.get_list(data)

    assert len(notes) == 1
    assert notes[0].title == "First Test"
    assert notes[0].source == ModelSource.MANUAL
    assert "fastapi" in notes[0].tags
