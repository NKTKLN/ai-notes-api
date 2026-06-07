"""Tests for note repository."""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import ModelSource, Note
from ai_notes_api.repositories import NoteListFilters
from ai_notes_api.repositories.note import NoteRepository


def create_note(
    *,
    title: str = "Test note",
    content: str = "Test content",
    tags: list[str] | None = None,
    source: ModelSource = ModelSource.MANUAL,
    model_name: str | None = None,
) -> Note:
    """Create a note instance for repository tests.

    Args:
        title (str): Note title.
        content (str): Note content.
        tags (list[str] | None): Note tags.
        source (ModelSource): Note source.
        model_name (str | None): Name of the model associated with the note.

    Returns:
        Note: Note model instance.
    """
    return Note(
        title=title,
        content=content,
        tags=tags or [],
        source=source,
        model_name=model_name,
    )


@pytest.mark.asyncio
async def test_create_note_success(async_session: AsyncSession) -> None:
    """Test successful note creation."""
    repository = NoteRepository(session=async_session)

    note = create_note(
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    created_note = await repository.create(note)

    assert created_note.id is not None
    assert created_note.title == "Test"
    assert created_note.content == "Content"
    assert created_note.tags == ["fastapi"]
    assert created_note.source == ModelSource.MANUAL
    assert created_note.deleted_at is None


@pytest.mark.asyncio
async def test_get_note_success(async_session: AsyncSession) -> None:
    """Test successful note retrieval by identifier."""
    repository = NoteRepository(session=async_session)

    created_note = await repository.create(
        create_note(
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    note = await repository.get_by_id(created_note.id)

    assert note is not None
    assert note.id == created_note.id
    assert note.title == "Test"
    assert note.content == "Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_get_note_not_found(async_session: AsyncSession) -> None:
    """Test that note retrieval returns None when the note is not found."""
    repository = NoteRepository(session=async_session)

    note = await repository.get_by_id(999)

    assert note is None


@pytest.mark.asyncio
async def test_get_note_soft_deleted_not_found(async_session: AsyncSession) -> None:
    """Test that soft-deleted note retrieval returns None."""
    repository = NoteRepository(session=async_session)

    created_note = await repository.create(
        create_note(
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(created_note)

    note = await repository.get_by_id(created_note.id)

    assert note is None


@pytest.mark.asyncio
async def test_get_notes_list_success(async_session: AsyncSession) -> None:
    """Test successful notes list retrieval."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="First Test",
            content="First Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="Second Test",
            content="Second Content",
            tags=[],
            source=ModelSource.API,
        )
    )

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(filters)

    assert len(notes) == 2
    assert notes[0].title == "Second Test"
    assert notes[1].title == "First Test"


@pytest.mark.asyncio
async def test_get_notes_list_empty_success(async_session: AsyncSession) -> None:
    """Test successful empty notes list retrieval."""
    repository = NoteRepository(session=async_session)

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(filters)

    assert notes == []


@pytest.mark.asyncio
async def test_get_notes_list_excludes_deleted(async_session: AsyncSession) -> None:
    """Test that notes list excludes soft-deleted notes."""
    repository = NoteRepository(session=async_session)

    active_note = await repository.create(
        create_note(
            title="Active Test",
            content="Active Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    deleted_note = await repository.create(
        create_note(
            title="Deleted Test",
            content="Deleted Content",
            tags=["deleted"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(deleted_note)

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].id == active_note.id
    assert notes[0].title == "Active Test"


@pytest.mark.asyncio
async def test_get_notes_list_with_source_filter_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval filtered by source."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="Manual Test",
            content="Manual Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="API Test",
            content="API Content",
            tags=["api"],
            source=ModelSource.API,
        )
    )

    filters = NoteListFilters(
        source=ModelSource.API,
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "API Test"
    assert notes[0].source == ModelSource.API


@pytest.mark.asyncio
async def test_get_notes_list_with_tag_filter_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval filtered by tag."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="FastAPI Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="SQLAlchemy Test",
            content="SQLAlchemy Content",
            tags=["sqlalchemy"],
            source=ModelSource.MANUAL,
        )
    )

    filters = NoteListFilters(
        tag="fastapi",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"
    assert notes[0].tags == ["fastapi", "python"]


@pytest.mark.asyncio
async def test_get_notes_list_with_model_name_filter_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval filtered by model name."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="GPT Test",
            content="GPT Content",
            tags=["ai"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            title="Claude Test",
            content="Claude Content",
            tags=["ai"],
            source=ModelSource.API,
            model_name="claude-3-5-sonnet",
        )
    )

    filters = NoteListFilters(
        model_name="gpt-4o",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "GPT Test"
    assert notes[0].model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_get_notes_list_with_search_in_title_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval filtered by title search."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="FastAPI Test",
            content="Some Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="Django Test",
            content="Some Content",
            tags=["django"],
            source=ModelSource.MANUAL,
        )
    )

    filters = NoteListFilters(
        search="fastapi",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"


@pytest.mark.asyncio
async def test_get_notes_list_with_search_in_content_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval filtered by content search."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="First Test",
            content="This note mentions SQLAlchemy",
            tags=["python"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="Second Test",
            content="This note mentions Django",
            tags=["python"],
            source=ModelSource.MANUAL,
        )
    )

    filters = NoteListFilters(
        search="sqlalchemy",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "First Test"


@pytest.mark.asyncio
async def test_get_notes_list_with_search_whitespace_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval with whitespace around search query."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="FastAPI Test",
            content="Some Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="Django Test",
            content="Some Content",
            tags=["django"],
            source=ModelSource.MANUAL,
        )
    )

    filters = NoteListFilters(
        search="   fastapi   ",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"


@pytest.mark.asyncio
async def test_get_notes_list_with_empty_search_success(
    async_session: AsyncSession,
) -> None:
    """Test successful notes list retrieval with empty search query."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="First Test",
            content="First Content",
            tags=["first"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            title="Second Test",
            content="Second Content",
            tags=["second"],
            source=ModelSource.API,
        )
    )

    filters = NoteListFilters(
        search="",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 2


@pytest.mark.asyncio
async def test_get_notes_list_with_filters_success(async_session: AsyncSession) -> None:
    """Test successful notes list retrieval with multiple filters."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            title="Matching Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            title="Wrong Source Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.MANUAL,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            title="Wrong Tag Test",
            content="FastAPI Content",
            tags=["django"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            title="Wrong Model Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.API,
            model_name="claude-3-5-sonnet",
        )
    )

    filters = NoteListFilters(
        source=ModelSource.API,
        tag="fastapi",
        model_name="gpt-4o",
        search="fastapi",
        limit=10,
        offset=0,
    )

    notes = await repository.get_list(filters)

    assert len(notes) == 1
    assert notes[0].title == "Matching Test"
    assert notes[0].source == ModelSource.API
    assert notes[0].tags == ["fastapi", "python"]
    assert notes[0].model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_get_notes_list_with_limit_success(async_session: AsyncSession) -> None:
    """Test successful notes list retrieval with limit."""
    repository = NoteRepository(session=async_session)

    await repository.create(create_note(title="First Test"))
    await repository.create(create_note(title="Second Test"))
    await repository.create(create_note(title="Third Test"))

    filters = NoteListFilters(limit=2, offset=0)

    notes = await repository.get_list(filters)

    assert len(notes) == 2


@pytest.mark.asyncio
async def test_get_notes_list_with_offset_success(async_session: AsyncSession) -> None:
    """Test successful notes list retrieval with offset."""
    repository = NoteRepository(session=async_session)

    first_note = await repository.create(create_note(title="First Test"))
    second_note = await repository.create(create_note(title="Second Test"))
    third_note = await repository.create(create_note(title="Third Test"))

    filters = NoteListFilters(limit=10, offset=1)

    notes = await repository.get_list(filters)

    assert len(notes) == 2
    assert notes[0].id == second_note.id
    assert notes[1].id == first_note.id
    assert third_note.id not in [note.id for note in notes]


@pytest.mark.asyncio
async def test_update_note_success(async_session: AsyncSession) -> None:
    """Test successful note update."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            title="Old Test",
            content="Old Content",
            tags=[],
            source=ModelSource.MANUAL,
        )
    )

    note.title = "New Test"
    note.content = "New Content"
    note.tags = ["fastapi"]
    note.source = ModelSource.API
    note.model_name = "gpt-4o"

    updated_note = await repository.update(note)

    assert updated_note.id == note.id
    assert updated_note.title == "New Test"
    assert updated_note.content == "New Content"
    assert updated_note.tags == ["fastapi"]
    assert updated_note.source == ModelSource.API
    assert updated_note.model_name == "gpt-4o"

    found_note = await repository.get_by_id(note.id)

    assert found_note is not None
    assert found_note.title == "New Test"
    assert found_note.content == "New Content"
    assert found_note.tags == ["fastapi"]
    assert found_note.source == ModelSource.API
    assert found_note.model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_delete_note_success(async_session: AsyncSession) -> None:
    """Test successful note soft deletion."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(note)

    assert note.deleted_at is not None
    assert isinstance(note.deleted_at, datetime)


@pytest.mark.asyncio
async def test_delete_note_hides_note_success(async_session: AsyncSession) -> None:
    """Test that soft deletion hides note from repository reads."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(note)

    found_note = await repository.get_by_id(note.id)

    assert found_note is None


@pytest.mark.asyncio
async def test_delete_note_preserves_database_row_success(
    async_session: AsyncSession,
) -> None:
    """Test that soft deletion preserves the database row."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(note)

    result = await async_session.execute(select(Note).where(Note.id == note.id))
    stored_note = result.scalar_one_or_none()

    assert stored_note is not None
    assert stored_note.id == note.id
    assert stored_note.deleted_at is not None
