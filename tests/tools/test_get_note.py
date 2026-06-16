"""Tests for the get note by ID built-in tool."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import ModelSource
from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import make_get_note_by_id_tool

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeNoteService:
    """Fake note service recording calls for get_note_by_id testing."""

    def __init__(self, note: Any = None) -> None:
        """Initialize the fake note service."""
        self.note = note
        self.received_user_id: UUID | None = None
        self.received_note_id: UUID | None = None

    async def get_note(self, user_id: UUID, note_id: UUID) -> Any:
        """Record the call and return the configured note."""
        self.received_user_id = user_id
        self.received_note_id = note_id
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
    """Build the get_note_by_id tool wired with a fake note service."""
    notes_service = FakeNoteService(note=note)
    tool = make_get_note_by_id_tool(
        notes_service=cast(NoteService, notes_service),
        user_id=TEST_USER_ID,
    )
    return notes_service, tool


def test_tool_definition_has_expected_metadata() -> None:
    """Test that the tool definition exposes the expected name and schema."""
    _, tool = _build_tool()

    assert tool["name"] == "get_note_by_id"
    assert tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert callable(tool["handler"])
    assert set(tool["parameters"]["properties"]) == {"note_id"}
    assert tool["parameters"]["required"] == ["note_id"]


@pytest.mark.asyncio
async def test_handler_passes_identifiers_to_note_service() -> None:
    """Test that the handler forwards the user and note identifiers."""
    notes_service, tool = _build_tool(note=_note())

    await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert notes_service.received_user_id == TEST_USER_ID
    assert notes_service.received_note_id == TEST_NOTE_ID


@pytest.mark.asyncio
async def test_handler_serializes_note() -> None:
    """Test that the returned note is serialized into an LLM-friendly item."""
    _, tool = _build_tool(note=_note())

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
    """Test that note content is truncated to 1000 characters."""
    _, tool = _build_tool(note=_note(content="a" * 2000))

    result = await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert len(result["content"]) == 1000


@pytest.mark.asyncio
async def test_handler_rejects_invalid_note_id() -> None:
    """Test that a malformed note identifier raises a value error."""
    _, tool = _build_tool(note=_note())

    with pytest.raises(ValueError):
        await tool["handler"](note_id="not-a-uuid")
