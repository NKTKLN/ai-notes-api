"""Tests for the search notes built-in tool."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.db.models import ModelSource
from ai_notes_api.schemas import NoteListQuerySchema
from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import make_search_notes_tool

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeNoteService:
    """Fake note service recording calls for search_notes testing."""

    def __init__(self, notes: list[Any] | None = None) -> None:
        """Initialize the fake note service."""
        self.notes = notes or []
        self.received_user_id: UUID | None = None
        self.received_filters: NoteListQuerySchema | None = None

    async def get_notes_list(
        self,
        user_id: UUID,
        filters: NoteListQuerySchema,
    ) -> list[Any]:
        """Record the call and return the configured notes."""
        self.received_user_id = user_id
        self.received_filters = filters
        return self.notes


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


def _build_tool(notes: list[Any] | None = None) -> tuple[FakeNoteService, Any]:
    """Build the search_notes tool wired with a fake note service."""
    notes_service = FakeNoteService(notes=notes)
    tool = make_search_notes_tool(
        notes_service=cast(NoteService, notes_service),
        user_id=TEST_USER_ID,
    )
    return notes_service, tool


def test_tool_definition_has_expected_metadata() -> None:
    """Test that the tool definition exposes the expected name and schema."""
    _, tool = _build_tool()

    assert tool["name"] == "search_notes"
    assert tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert callable(tool["handler"])
    assert set(tool["parameters"]["properties"]) == {
        "limit",
        "offset",
        "search",
        "source",
        "tag",
        "model_name",
    }


@pytest.mark.asyncio
async def test_handler_passes_filters_to_note_service() -> None:
    """Test that handler arguments are forwarded as note list filters."""
    notes_service, tool = _build_tool()

    await tool["handler"](
        limit=10,
        offset=5,
        search="query",
        source="manual",
        tag="work",
        model_name="gpt-4",
    )

    assert notes_service.received_user_id == TEST_USER_ID
    filters = notes_service.received_filters
    assert filters is not None
    assert filters.limit == 10
    assert filters.offset == 5
    assert filters.search == "query"
    assert filters.source == ModelSource.MANUAL
    assert filters.tag == "work"
    assert filters.model_name == "gpt-4"


@pytest.mark.asyncio
async def test_handler_defaults_source_to_none() -> None:
    """Test that an omitted source results in a null source filter."""
    notes_service, tool = _build_tool()

    await tool["handler"]()

    filters = notes_service.received_filters
    assert filters is not None
    assert filters.source is None


@pytest.mark.asyncio
async def test_handler_serializes_notes() -> None:
    """Test that returned notes are serialized into LLM-friendly items."""
    note = _note()
    _, tool = _build_tool(notes=[note])

    result = await tool["handler"]()

    assert result == {
        "items": [
            {
                "id": str(TEST_NOTE_ID),
                "title": "Title",
                "content": "Content",
                "tags": ["tag"],
                "source": "manual",
                "model_name": "gpt-4",
                "created_at": "2026-06-16T00:00:00+00:00",
            }
        ]
    }


@pytest.mark.asyncio
async def test_handler_truncates_long_content() -> None:
    """Test that note content is truncated to 1000 characters."""
    note = _note(content="a" * 2000)
    _, tool = _build_tool(notes=[note])

    result = await tool["handler"]()

    assert len(result["items"][0]["content"]) == 1000


@pytest.mark.asyncio
async def test_handler_returns_empty_items_when_no_notes() -> None:
    """Test that an empty note list yields an empty items list."""
    _, tool = _build_tool(notes=[])

    result = await tool["handler"]()

    assert result == {"items": []}


@pytest.mark.asyncio
async def test_handler_rejects_invalid_source() -> None:
    """Test that an unknown source value raises a value error."""
    _, tool = _build_tool()

    with pytest.raises(ValueError):
        await tool["handler"](source="unknown")
