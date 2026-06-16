"""Tests for the create note built-in tool."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import ModelSource
from ai_notes_api.schemas import NoteCreateSchema
from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import make_create_note_tool

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeNoteService:
    """Fake note service recording calls for create_note testing."""

    def __init__(self, note: Any = None) -> None:
        """Initialize the fake note service."""
        self.note = note
        self.received_user_id: UUID | None = None
        self.received_data: NoteCreateSchema | None = None

    async def create_note(self, user_id: UUID, data: NoteCreateSchema) -> Any:
        """Record the call and return the configured note."""
        self.received_user_id = user_id
        self.received_data = data
        return self.note


def _note(**overrides: Any) -> SimpleNamespace:
    """Return a note-like object with default attributes."""
    defaults = {
        "id": TEST_NOTE_ID,
        "title": "Title",
        "content": "Content",
        "tags": ["tag"],
        "source": ModelSource.LLM,
        "model_name": "gpt-4",
        "created_at": datetime(2026, 6, 16, tzinfo=UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_tool(note: Any = None) -> tuple[FakeNoteService, Any]:
    """Build the create_note tool wired with a fake note service."""
    notes_service = FakeNoteService(note=note or _note())
    tool = make_create_note_tool(
        notes_service=cast(NoteService, notes_service),
        user_id=TEST_USER_ID,
    )
    return notes_service, tool


def test_tool_definition_has_expected_metadata() -> None:
    """Test that the tool definition exposes the expected name and schema."""
    _, tool = _build_tool()

    assert tool["name"] == "create_note"
    assert tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert callable(tool["handler"])
    assert set(tool["parameters"]["properties"]) == {
        "title",
        "content",
        "tags",
        "model_name",
    }
    assert tool["parameters"]["required"] == ["title"]


@pytest.mark.asyncio
async def test_handler_passes_data_to_note_service() -> None:
    """Test that handler arguments are forwarded as note creation data."""
    notes_service, tool = _build_tool()

    await tool["handler"](
        title="My note",
        content="Body",
        tags=["work", "ideas"],
        model_name="gpt-4",
    )

    assert notes_service.received_user_id == TEST_USER_ID
    data = notes_service.received_data
    assert data is not None
    assert data.title == "My note"
    assert data.content == "Body"
    assert data.tags == ["work", "ideas"]
    assert data.model_name == "gpt-4"
    assert data.source == ModelSource.LLM


@pytest.mark.asyncio
async def test_handler_defaults_tags_to_empty_list() -> None:
    """Test that omitted tags result in an empty tag list."""
    notes_service, tool = _build_tool()

    await tool["handler"](title="My note")

    data = notes_service.received_data
    assert data is not None
    assert data.tags == []
    assert data.content == ""
    assert data.model_name is None


@pytest.mark.asyncio
async def test_handler_serializes_created_note() -> None:
    """Test that the created note is serialized into an LLM-friendly item."""
    _, tool = _build_tool()

    result = await tool["handler"](title="My note")

    assert result == {
        "id": str(TEST_NOTE_ID),
        "title": "Title",
        "content": "Content",
        "tags": ["tag"],
        "source": "llm",
        "model_name": "gpt-4",
        "created_at": "2026-06-16T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_handler_truncates_long_content() -> None:
    """Test that returned note content is truncated to 1000 characters."""
    _, tool = _build_tool(note=_note(content="a" * 2000))

    result = await tool["handler"](title="My note")

    assert len(result["content"]) == 1000


@pytest.mark.asyncio
async def test_handler_rejects_empty_title() -> None:
    """Test that an empty title raises a validation error."""
    _, tool = _build_tool()

    with pytest.raises(ValueError):
        await tool["handler"](title="")
