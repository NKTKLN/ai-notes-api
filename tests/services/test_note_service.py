"""Tests for note service."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from ai_notes_api.db.models import ModelSource, Note
from ai_notes_api.exceptions import NoteNotFoundError
from ai_notes_api.repositories import NoteListFilters
from ai_notes_api.repositories.note import NoteRepository
from ai_notes_api.schemas import NoteCreateSchema, NoteListQuerySchema, NoteUpdateSchema
from ai_notes_api.services import NoteService

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_ID_2 = UUID("44444444-4444-4444-4444-444444444444")
TEST_NOTE_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_NOTE_ID_2 = UUID("33333333-3333-3333-3333-333333333333")
TEST_NOTE_ID_3 = UUID("55555555-5555-5555-5555-555555555555")


class FakeNoteRepository:
    """Fake note repository used for testing note service behavior.

    Attributes:
        notes (dict[UUID, Note]): In-memory storage of notes by identifier.
        created_note (Note | None): Last note created through the fake repository.
    """

    def __init__(self) -> None:
        """Initialize the fake note repository."""
        self.notes: dict[UUID, Note] = {}
        self.created_note: Note | None = None

    async def create(self, note: Note) -> Note:
        """Create a note in the fake repository.

        Args:
            note (Note): Note instance to create.

        Returns:
            Note: Created note with assigned identifier.
        """
        note.id = TEST_NOTE_ID
        self.created_note = note
        self.notes[note.id] = note
        return note

    async def get_by_id(self, user_id: UUID, note_id: UUID) -> Note | None:
        """Return a note by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the note.
            note_id (UUID): Unique note identifier.

        Returns:
            Note | None: Matching note if found; otherwise, None.
        """
        note = self.notes.get(note_id)

        if note is not None and note.user_id == user_id:
            return note

        return None

    async def get_list(self, user_id: UUID, filters: NoteListFilters) -> list[Note]:
        """Return notes matching the provided filters.

        Args:
            user_id (UUID): Unique identifier of the user whose notes are requested.
            filters (NoteListFilters): Filters and pagination parameters.

        Returns:
            list[Note]: List of matching non-deleted notes.
        """
        notes = [
            note
            for note in self.notes.values()
            if note.deleted_at is None and note.user_id == user_id
        ]

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

    note = await service.create_note(TEST_USER_ID, data)

    assert note.id == TEST_NOTE_ID
    assert note.user_id == TEST_USER_ID
    assert note.title == "Test"
    assert note.content == "Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_get_note_success() -> None:
    """Test successful note retrieval by identifier."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    note = await service.get_note(TEST_USER_ID, TEST_NOTE_ID)

    assert note.title == "Test"


@pytest.mark.asyncio
async def test_get_note_not_found_by_id() -> None:
    """Test that note retrieval raises an error when the note is not found."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    with pytest.raises(NoteNotFoundError):
        await service.get_note(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_get_note_not_found_for_another_user() -> None:
    """Test that another user's note cannot be retrieved."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    with pytest.raises(NoteNotFoundError):
        await service.get_note(TEST_USER_ID_2, TEST_NOTE_ID)


@pytest.mark.asyncio
async def test_update_note_success() -> None:
    """Test successful note update."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
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

    note = await service.update_note(TEST_USER_ID, TEST_NOTE_ID, data)

    assert note.title == "New Test"
    assert note.content == "New Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_update_note_not_found_by_id() -> None:
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
        await service.update_note(TEST_USER_ID, uuid4(), data)


@pytest.mark.asyncio
async def test_update_note_not_found_for_another_user() -> None:
    """Test that another user's note cannot be updated."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
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

    with pytest.raises(NoteNotFoundError):
        await service.update_note(TEST_USER_ID_2, TEST_NOTE_ID, data)


@pytest.mark.asyncio
async def test_delete_note_success() -> None:
    """Test successful note deletion."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    await service.delete_note(TEST_USER_ID, TEST_NOTE_ID)

    assert repository.notes[TEST_NOTE_ID].deleted_at is not None


@pytest.mark.asyncio
async def test_delete_note_not_found_by_id() -> None:
    """Test that note deletion raises an error when the note is not found."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    with pytest.raises(NoteNotFoundError):
        await service.delete_note(TEST_USER_ID, uuid4())


@pytest.mark.asyncio
async def test_delete_note_not_found_for_another_user() -> None:
    """Test that another user's note cannot be deleted."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    with pytest.raises(NoteNotFoundError):
        await service.delete_note(TEST_USER_ID_2, TEST_NOTE_ID)


@pytest.mark.asyncio
async def test_get_notes_list_success() -> None:
    """Test successful notes list retrieval with filters."""
    repository = FakeNoteRepository()
    service = NoteService(repository=cast(NoteRepository, repository))

    repository.notes[TEST_NOTE_ID] = Note(
        id=TEST_NOTE_ID,
        user_id=TEST_USER_ID,
        title="First Test",
        content="First Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    repository.notes[TEST_NOTE_ID_2] = Note(
        id=TEST_NOTE_ID_2,
        user_id=TEST_USER_ID,
        title="Second Test",
        content="Second Content",
        tags=[],
        source=ModelSource.API,
    )

    repository.notes[TEST_NOTE_ID_3] = Note(
        id=TEST_NOTE_ID_3,
        user_id=TEST_USER_ID_2,
        title="First Test",
        content="First Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    data = NoteListQuerySchema(
        limit=1,
        search="Test",
        source=ModelSource.MANUAL,
        tag="fastapi",
    )

    notes = await service.get_list(TEST_USER_ID, data)

    assert len(notes) == 1
    assert notes[0].title == "First Test"
    assert notes[0].user_id == TEST_USER_ID
    assert notes[0].source == ModelSource.MANUAL
    assert "fastapi" in notes[0].tags
