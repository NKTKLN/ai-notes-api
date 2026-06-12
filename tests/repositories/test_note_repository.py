"""Tests for note repository."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from ai_notes_api.db.models import ModelSource, Note, User
except ImportError:
    from ai_notes_api.db.models import ModelSource, Note
    from ai_notes_api.db.models.user import User

from ai_notes_api.repositories import NoteListFilters
from ai_notes_api.repositories.note import NoteRepository


@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def other_user(async_session: AsyncSession) -> User:
    """Create another test user."""
    user = User(
        email="other-user@example.com",
        username="other_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )

    async_session.add(user)
    await async_session.flush()
    await async_session.refresh(user)

    return user


def create_note(  # noqa: PLR0913
    *,
    user_id: UUID,
    title: str = "Test note",
    content: str = "Test content",
    tags: list[str] | None = None,
    source: ModelSource = ModelSource.MANUAL,
    model_name: str | None = None,
) -> Note:
    """Create a note instance for repository tests.

    Args:
        user_id (UUID): Identifier of the user who owns the note.
        title (str): Note title.
        content (str): Note content.
        tags (list[str] | None): Note tags.
        source (ModelSource): Note source.
        model_name (str | None): Name of the model associated with the note.

    Returns:
        Note: Note model instance.
    """
    return Note(
        user_id=user_id,
        title=title,
        content=content,
        tags=tags or [],
        source=source,
        model_name=model_name,
    )


@pytest.mark.asyncio
async def test_create_note_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful note creation."""
    repository = NoteRepository(session=async_session)

    note = create_note(
        user_id=test_user.id,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    created_note = await repository.create(note)

    assert created_note.id is not None
    assert created_note.user_id == test_user.id
    assert created_note.title == "Test"
    assert created_note.content == "Content"
    assert created_note.tags == ["fastapi"]
    assert created_note.source == ModelSource.MANUAL
    assert created_note.deleted_at is None


@pytest.mark.asyncio
async def test_get_note_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful note retrieval by identifier."""
    repository = NoteRepository(session=async_session)

    created_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    note = await repository.get_by_id(test_user.id, created_note.id)

    assert note is not None
    assert note.id == created_note.id
    assert note.user_id == test_user.id
    assert note.title == "Test"
    assert note.content == "Content"
    assert note.tags == ["fastapi"]
    assert note.source == ModelSource.MANUAL


@pytest.mark.asyncio
async def test_get_note_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that note retrieval returns None when the note is not found."""
    repository = NoteRepository(session=async_session)

    note = await repository.get_by_id(test_user.id, uuid4())

    assert note is None


@pytest.mark.asyncio
async def test_get_note_soft_deleted_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft-deleted note retrieval returns None."""
    repository = NoteRepository(session=async_session)

    created_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(created_note)

    note = await repository.get_by_id(test_user.id, created_note.id)

    assert note is None


@pytest.mark.asyncio
async def test_get_note_by_id_returns_only_user_owned_note(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that note retrieval is scoped to the note owner."""
    repository = NoteRepository(session=async_session)

    owned_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Owned Test",
            content="Owned Content",
        )
    )

    other_note = await repository.create(
        create_note(
            user_id=other_user.id,
            title="Other Test",
            content="Other Content",
        )
    )

    found_note = await repository.get_by_id(test_user.id, owned_note.id)
    forbidden_note = await repository.get_by_id(test_user.id, other_note.id)

    assert found_note is not None
    assert found_note.id == owned_note.id
    assert found_note.user_id == test_user.id
    assert forbidden_note is None


@pytest.mark.asyncio
async def test_get_note_by_id_other_user_cannot_access_note(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that another user cannot access a note by identifier."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Private Test",
            content="Private Content",
        )
    )

    found_note = await repository.get_by_id(other_user.id, note.id)

    assert found_note is None


@pytest.mark.asyncio
async def test_get_notes_list_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="First Test",
            content="First Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Second Test",
            content="Second Content",
            tags=[],
            source=ModelSource.API,
        )
    )

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 2
    assert notes[0].title == "Second Test"
    assert notes[1].title == "First Test"
    assert all(note.user_id == test_user.id for note in notes)


@pytest.mark.asyncio
async def test_get_notes_list_empty_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful empty notes list retrieval."""
    repository = NoteRepository(session=async_session)

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(test_user.id, filters)

    assert notes == []


@pytest.mark.asyncio
async def test_get_notes_list_returns_only_user_owned_notes(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that notes list is scoped to the requested user."""
    repository = NoteRepository(session=async_session)

    owned_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Owned Test",
            content="Owned Content",
        )
    )

    await repository.create(
        create_note(
            user_id=other_user.id,
            title="Other User Test",
            content="Other User Content",
        )
    )

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].id == owned_note.id
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_empty_for_user_without_notes(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that a user without notes receives an empty list."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Owned Test",
            content="Owned Content",
        )
    )

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(other_user.id, filters)

    assert notes == []


@pytest.mark.asyncio
async def test_get_notes_list_excludes_deleted(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that notes list excludes soft-deleted notes."""
    repository = NoteRepository(session=async_session)

    active_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Active Test",
            content="Active Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    deleted_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Deleted Test",
            content="Deleted Content",
            tags=["deleted"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(deleted_note)

    filters = NoteListFilters(limit=10, offset=0)

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].id == active_note.id
    assert notes[0].title == "Active Test"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_source_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval filtered by source."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Manual Test",
            content="Manual Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "API Test"
    assert notes[0].source == ModelSource.API
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_tag_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval filtered by tag."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="FastAPI Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"
    assert notes[0].tags == ["fastapi", "python"]
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_model_name_filter_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval filtered by model name."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="GPT Test",
            content="GPT Content",
            tags=["ai"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "GPT Test"
    assert notes[0].model_name == "gpt-4o"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_search_in_title_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval filtered by title search."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="FastAPI Test",
            content="Some Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_search_in_content_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval filtered by content search."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="First Test",
            content="This note mentions SQLAlchemy",
            tags=["python"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "First Test"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_search_whitespace_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval with whitespace around search query."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="FastAPI Test",
            content="Some Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "FastAPI Test"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_empty_search_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval with empty search query."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="First Test",
            content="First Content",
            tags=["first"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 2
    assert all(note.user_id == test_user.id for note in notes)


@pytest.mark.asyncio
async def test_get_notes_list_with_filters_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval with multiple filters."""
    repository = NoteRepository(session=async_session)

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Matching Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Wrong Source Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.MANUAL,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
            title="Wrong Tag Test",
            content="FastAPI Content",
            tags=["django"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            user_id=test_user.id,
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].title == "Matching Test"
    assert notes[0].source == ModelSource.API
    assert notes[0].tags == ["fastapi", "python"]
    assert notes[0].model_name == "gpt-4o"
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_filters_do_not_leak_other_user_notes(
    async_session: AsyncSession,
    test_user: User,
    other_user: User,
) -> None:
    """Test that filters are applied only inside the requested user's notes."""
    repository = NoteRepository(session=async_session)

    owned_note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Matching Owned Test",
            content="FastAPI Content",
            tags=["fastapi"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    )

    await repository.create(
        create_note(
            user_id=other_user.id,
            title="Matching Other Test",
            content="FastAPI Content",
            tags=["fastapi"],
            source=ModelSource.API,
            model_name="gpt-4o",
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

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 1
    assert notes[0].id == owned_note.id
    assert notes[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_get_notes_list_with_limit_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval with limit."""
    repository = NoteRepository(session=async_session)

    await repository.create(create_note(user_id=test_user.id, title="First Test"))
    await repository.create(create_note(user_id=test_user.id, title="Second Test"))
    await repository.create(create_note(user_id=test_user.id, title="Third Test"))

    filters = NoteListFilters(limit=2, offset=0)

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 2
    assert all(note.user_id == test_user.id for note in notes)


@pytest.mark.asyncio
async def test_get_notes_list_with_offset_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful notes list retrieval with offset."""
    repository = NoteRepository(session=async_session)

    first_note = await repository.create(
        create_note(user_id=test_user.id, title="First Test")
    )
    second_note = await repository.create(
        create_note(user_id=test_user.id, title="Second Test")
    )
    third_note = await repository.create(
        create_note(user_id=test_user.id, title="Third Test")
    )

    filters = NoteListFilters(limit=10, offset=1)

    notes = await repository.get_list(test_user.id, filters)

    assert len(notes) == 2
    assert notes[0].id == second_note.id
    assert notes[1].id == first_note.id
    assert third_note.id not in [note.id for note in notes]
    assert all(note.user_id == test_user.id for note in notes)


@pytest.mark.asyncio
async def test_update_note_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful note update."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
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
    assert updated_note.user_id == test_user.id
    assert updated_note.title == "New Test"
    assert updated_note.content == "New Content"
    assert updated_note.tags == ["fastapi"]
    assert updated_note.source == ModelSource.API
    assert updated_note.model_name == "gpt-4o"

    found_note = await repository.get_by_id(test_user.id, note.id)

    assert found_note is not None
    assert found_note.user_id == test_user.id
    assert found_note.title == "New Test"
    assert found_note.content == "New Content"
    assert found_note.tags == ["fastapi"]
    assert found_note.source == ModelSource.API
    assert found_note.model_name == "gpt-4o"


@pytest.mark.asyncio
async def test_delete_note_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test successful note soft deletion."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
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
async def test_delete_note_hides_note_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion hides note from repository reads."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Test",
            content="Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        )
    )

    await repository.soft_delete(note)

    found_note = await repository.get_by_id(test_user.id, note.id)

    assert found_note is None


@pytest.mark.asyncio
async def test_get_note_soft_deleted_for_owner_not_found(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that owner cannot retrieve a soft-deleted note."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
            title="Deleted Test",
            content="Deleted Content",
        )
    )

    await repository.soft_delete(note)

    found_note = await repository.get_by_id(test_user.id, note.id)

    assert found_note is None


@pytest.mark.asyncio
async def test_delete_note_preserves_database_row_success(
    async_session: AsyncSession,
    test_user: User,
) -> None:
    """Test that soft deletion preserves the database row."""
    repository = NoteRepository(session=async_session)

    note = await repository.create(
        create_note(
            user_id=test_user.id,
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
    assert stored_note.user_id == test_user.id
    assert stored_note.deleted_at is not None
