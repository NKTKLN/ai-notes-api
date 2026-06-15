"""Tests for notes API router."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_notes_api.api.v1.dependencies import get_current_user, get_note_service
from ai_notes_api.api.v1.notes import router
from ai_notes_api.db.models import ModelSource, User
from ai_notes_api.schemas import NoteResponseSchema

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_NOTE_ID_2 = UUID("33333333-3333-3333-3333-333333333333")


def create_test_user() -> User:
    """Create current user for router tests.

    Returns:
        User: Test user model instance.
    """
    return User(
        id=TEST_USER_ID,
        email="test-user@example.com",
        username="test_user",
        hashed_password="test-password-hash",  # noqa: S106
        is_active=True,
        is_superuser=False,
    )


def create_note_response(  # noqa: PLR0913
    *,
    note_id: UUID = TEST_NOTE_ID,
    title: str = "Test note",
    content: str = "Test content",
    tags: list[str] | None = None,
    source: ModelSource = ModelSource.MANUAL,
    model_name: str | None = None,
) -> NoteResponseSchema:
    """Create note response schema for router tests.

    Args:
        note_id (UUID): Unique note identifier.
        title (str): Note title.
        content (str): Note content.
        tags (list[str] | None): Optional note tags.
        source (ModelSource): Note source.
        model_name (str | None): Optional name of the model associated with the note.

    Returns:
        NoteResponseSchema: Note response schema instance.
    """
    now = datetime.now(UTC)

    return NoteResponseSchema(
        id=note_id,
        title=title,
        content=content,
        tags=tags or [],
        source=source,
        model_name=model_name,
        model_metadata={},
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def current_user() -> User:
    """Create mocked current user.

    Returns:
        User: Current authenticated user.
    """
    return create_test_user()


@pytest.fixture
def note_service_mock() -> AsyncMock:
    """Create mocked note service.

    Returns:
        AsyncMock: Mocked note service dependency.
    """
    return AsyncMock()


@pytest.fixture
def client(
    note_service_mock: AsyncMock,
    current_user: User,
) -> TestClient:
    """Create a test client with mocked dependencies.

    Args:
        note_service_mock (AsyncMock): Mocked note service dependency.
        current_user (User): Mocked authenticated user.

    Returns:
        TestClient: FastAPI test client.
    """
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_note_service] = lambda: note_service_mock
    app.dependency_overrides[get_current_user] = lambda: current_user

    return TestClient(app)


def test_create_note_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful note creation."""
    note = create_note_response(
        note_id=TEST_NOTE_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )
    note_service_mock.create_note.return_value = note

    response = client.post(
        "/notes",
        json={
            "title": "Test",
            "content": "Content",
            "tags": ["fastapi"],
            "source": ModelSource.MANUAL.value,
            "model_name": None,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == str(TEST_NOTE_ID)
    assert data["title"] == "Test"
    assert data["content"] == "Content"
    assert data["tags"] == ["fastapi"]
    assert data["source"] == ModelSource.MANUAL.value
    assert data["model_name"] is None

    note_service_mock.create_note.assert_awaited_once()

    user_id, create_data = note_service_mock.create_note.await_args.args

    assert user_id == TEST_USER_ID
    assert create_data.title == "Test"
    assert create_data.content == "Content"
    assert create_data.tags == ["fastapi"]
    assert create_data.source == ModelSource.MANUAL


def test_get_notes_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful notes list retrieval."""
    note_service_mock.get_notes_list.return_value = [
        create_note_response(
            note_id=TEST_NOTE_ID_2,
            title="Second Test",
            content="Second Content",
            tags=[],
            source=ModelSource.API,
        ),
        create_note_response(
            note_id=TEST_NOTE_ID,
            title="First Test",
            content="First Content",
            tags=["fastapi"],
            source=ModelSource.MANUAL,
        ),
    ]

    response = client.get("/notes?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 2
    assert len(data["items"]) == 2

    assert data["items"][0]["id"] == str(TEST_NOTE_ID_2)
    assert data["items"][0]["title"] == "Second Test"
    assert data["items"][0]["source"] == ModelSource.API.value

    assert data["items"][1]["id"] == str(TEST_NOTE_ID)
    assert data["items"][1]["title"] == "First Test"
    assert data["items"][1]["source"] == ModelSource.MANUAL.value

    note_service_mock.get_notes_list.assert_awaited_once()

    user_id, filters = note_service_mock.get_notes_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_notes_empty_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful empty notes list retrieval."""
    note_service_mock.get_notes_list.return_value = []

    response = client.get("/notes?limit=10&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert data["total"] == 0

    note_service_mock.get_notes_list.assert_awaited_once()

    user_id, filters = note_service_mock.get_notes_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_notes_with_filters_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful notes list retrieval with filters."""
    note_service_mock.get_notes_list.return_value = [
        create_note_response(
            note_id=TEST_NOTE_ID,
            title="Matching Test",
            content="FastAPI Content",
            tags=["fastapi", "python"],
            source=ModelSource.API,
            model_name="gpt-4o",
        )
    ]

    response = client.get(
        "/notes",
        params={
            "source": ModelSource.API.value,
            "tag": "fastapi",
            "model_name": "gpt-4o",
            "search": "fastapi",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]

    assert item["id"] == str(TEST_NOTE_ID)
    assert item["title"] == "Matching Test"
    assert item["content"] == "FastAPI Content"
    assert item["tags"] == ["fastapi", "python"]
    assert item["source"] == ModelSource.API.value
    assert item["model_name"] == "gpt-4o"

    note_service_mock.get_notes_list.assert_awaited_once()

    user_id, filters = note_service_mock.get_notes_list.await_args.args

    assert user_id == TEST_USER_ID
    assert filters.source == ModelSource.API
    assert filters.tag == "fastapi"
    assert filters.model_name == "gpt-4o"
    assert filters.search == "fastapi"
    assert filters.limit == 10
    assert filters.offset == 0


def test_get_note_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful note retrieval by identifier."""
    note_service_mock.get_note.return_value = create_note_response(
        note_id=TEST_NOTE_ID,
        title="Test",
        content="Content",
        tags=["fastapi"],
        source=ModelSource.MANUAL,
    )

    response = client.get(f"/notes/{TEST_NOTE_ID}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_NOTE_ID)
    assert data["title"] == "Test"
    assert data["content"] == "Content"
    assert data["tags"] == ["fastapi"]
    assert data["source"] == ModelSource.MANUAL.value

    note_service_mock.get_note.assert_awaited_once_with(TEST_USER_ID, TEST_NOTE_ID)


def test_update_note_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful note update."""
    note_service_mock.update_note.return_value = create_note_response(
        note_id=TEST_NOTE_ID,
        title="New Test",
        content="New Content",
        tags=["fastapi"],
        source=ModelSource.API,
        model_name="gpt-4o",
    )

    response = client.patch(
        f"/notes/{TEST_NOTE_ID}",
        json={
            "title": "New Test",
            "content": "New Content",
            "tags": ["fastapi"],
            "source": ModelSource.API.value,
            "model_name": "gpt-4o",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(TEST_NOTE_ID)
    assert data["title"] == "New Test"
    assert data["content"] == "New Content"
    assert data["tags"] == ["fastapi"]
    assert data["source"] == ModelSource.API.value
    assert data["model_name"] == "gpt-4o"

    note_service_mock.update_note.assert_awaited_once()

    user_id, note_id, update_data = note_service_mock.update_note.await_args.args

    assert user_id == TEST_USER_ID
    assert note_id == TEST_NOTE_ID
    assert update_data.title == "New Test"
    assert update_data.content == "New Content"
    assert update_data.tags == ["fastapi"]
    assert update_data.source == ModelSource.API
    assert update_data.model_name == "gpt-4o"


def test_delete_note_success(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test successful note deletion."""
    note_service_mock.delete_note.return_value = None

    response = client.delete(f"/notes/{TEST_NOTE_ID}")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted"}

    note_service_mock.delete_note.assert_awaited_once_with(TEST_USER_ID, TEST_NOTE_ID)


def test_create_note_uses_current_user_id(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test that note creation passes current user id to service."""
    note_service_mock.create_note.return_value = create_note_response(
        note_id=TEST_NOTE_ID
    )

    response = client.post(
        "/notes",
        json={
            "title": "Test note",
            "content": "Test content",
            "tags": [],
            "source": ModelSource.MANUAL.value,
            "model_name": None,
        },
    )

    assert response.status_code == 201

    note_service_mock.create_note.assert_awaited_once()

    user_id, _ = note_service_mock.create_note.await_args.args

    assert user_id == TEST_USER_ID


def test_get_notes_uses_current_user_id(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test that notes list retrieval passes current user id to service."""
    note_service_mock.get_notes_list.return_value = []

    response = client.get("/notes")

    assert response.status_code == 200

    note_service_mock.get_notes_list.assert_awaited_once()

    user_id, _ = note_service_mock.get_notes_list.await_args.args

    assert user_id == TEST_USER_ID


def test_get_note_uses_current_user_id(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test that note retrieval passes current user id to service."""
    note_service_mock.get_note.return_value = create_note_response(note_id=TEST_NOTE_ID)

    response = client.get(f"/notes/{TEST_NOTE_ID}")

    assert response.status_code == 200

    note_service_mock.get_note.assert_awaited_once_with(TEST_USER_ID, TEST_NOTE_ID)


def test_update_note_uses_current_user_id(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test that note update passes current user id to service."""
    note_service_mock.update_note.return_value = create_note_response(
        note_id=TEST_NOTE_ID,
        title="Updated",
        content="Updated content",
    )

    response = client.patch(
        f"/notes/{TEST_NOTE_ID}",
        json={
            "title": "Updated",
            "content": "Updated content",
        },
    )

    assert response.status_code == 200

    note_service_mock.update_note.assert_awaited_once()

    user_id, note_id, _ = note_service_mock.update_note.await_args.args

    assert user_id == TEST_USER_ID
    assert note_id == TEST_NOTE_ID


def test_delete_note_uses_current_user_id(
    client: TestClient,
    note_service_mock: AsyncMock,
) -> None:
    """Test that note deletion passes current user id to service."""
    note_service_mock.delete_note.return_value = None

    response = client.delete(f"/notes/{TEST_NOTE_ID}")

    assert response.status_code == 200

    note_service_mock.delete_note.assert_awaited_once_with(TEST_USER_ID, TEST_NOTE_ID)
