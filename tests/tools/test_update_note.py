"""Tests for the update note built-in tool."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import ModelSource
from ai_notes_api.schemas import NoteUpdateSchema
from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import make_update_note_tool

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeNoteService:
    """Fake note service recording calls for update_note testing."""

    def __init__(self, note: Any = None) -> None:
        """Initialize the fake note service."""
        self.note = note
        self.received_user_id: UUID | None = None
        self.received_note_id: UUID | None = None
        self.received_update: NoteUpdateSchema | None = None

    async def update_note(
        self,
        user_id: UUID,
        note_id: UUID,
        note_update: NoteUpdateSchema,
    ) -> Any:
        """Record the call and return the configured note."""
        self.received_user_id = user_id
        self.received_note_id = note_id
        self.received_update = note_update
        return self.note


def _note(**overrides: Any) -> SimpleNamespace:
    """Return a note-like object with default attributes."""
    defaults = {
        "id": TEST_NOTE_ID,
        "title": "Title",
        "content": "Content",
        "tags": ["tag"],
        "source": ModelSource.MANUAL,
        "model_name": "gpt-4",
        "created_at": datetime(2026, 6, 16, tzinfo=UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _build_tool(note: Any = None) -> tuple[FakeNoteService, Any]:
    """Build the update_note tool wired with a fake note service."""
    notes_service = FakeNoteService(note=note or _note())
    tool = make_update_note_tool(
        notes_service=cast(NoteService, notes_service),
        user_id=TEST_USER_ID,
    )
    return notes_service, tool


def test_tool_definition_has_expected_metadata() -> None:
    """Test that the tool definition exposes the expected name and schema."""
    _, tool = _build_tool()

    assert tool["name"] == "update_note"
    assert tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert callable(tool["handler"])
    assert set(tool["parameters"]["properties"]) == {
        "note_id",
        "title",
        "content",
        "tags",
        "source",
        "model_name",
    }
    assert tool["parameters"]["required"] == ["note_id"]


@pytest.mark.asyncio
async def test_handler_passes_update_to_note_service() -> None:
    """Test that handler arguments are forwarded as a note update."""
    notes_service, tool = _build_tool()

    await tool["handler"](
        note_id=str(TEST_NOTE_ID),
        title="New title",
        content="New content",
        tags=["work"],
        source="manual",
        model_name="gpt-4",
    )

    assert notes_service.received_user_id == TEST_USER_ID
    assert notes_service.received_note_id == TEST_NOTE_ID
    update = notes_service.received_update
    assert update is not None
    assert update.title == "New title"
    assert update.content == "New content"
    assert update.tags == ["work"]
    assert update.source == ModelSource.MANUAL
    assert update.model_name == "gpt-4"


@pytest.mark.asyncio
async def test_handler_defaults_unset_fields_to_none() -> None:
    """Test that omitted update fields stay unset."""
    notes_service, tool = _build_tool()

    await tool["handler"](note_id=str(TEST_NOTE_ID))

    update = notes_service.received_update
    assert update is not None
    assert update.title is None
    assert update.content is None
    assert update.tags is None
    assert update.source is None
    assert update.model_name is None


@pytest.mark.asyncio
async def test_handler_serializes_updated_note() -> None:
    """Test that the updated note is serialized into an LLM-friendly item."""
    _, tool = _build_tool()

    result = await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert result == {
        "id": str(TEST_NOTE_ID),
        "title": "Title",
        "content": "Content",
        "tags": ["tag"],
        "source": "manual",
        "model_name": "gpt-4",
        "created_at": "2026-06-16T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_handler_truncates_long_content() -> None:
    """Test that returned note content is truncated to 1000 characters."""
    _, tool = _build_tool(note=_note(content="a" * 2000))

    result = await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert len(result["content"]) == 1000


@pytest.mark.asyncio
async def test_handler_rejects_invalid_source() -> None:
    """Test that an unknown source value raises a value error."""
    _, tool = _build_tool()

    with pytest.raises(ValueError):
        await tool["handler"](note_id=str(TEST_NOTE_ID), source="unknown")


@pytest.mark.asyncio
async def test_handler_rejects_invalid_note_id() -> None:
    """Test that a malformed note identifier raises a value error."""
    _, tool = _build_tool()

    with pytest.raises(ValueError):
        await tool["handler"](note_id="not-a-uuid")
