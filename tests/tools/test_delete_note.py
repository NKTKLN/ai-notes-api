"""Tests for the delete note built-in tool."""

from typing import Any, cast
from uuid import UUID

import pytest

from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import make_delete_note_tool

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_NOTE_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeNoteService:
    """Fake note service recording calls for delete_note testing."""

    def __init__(self) -> None:
        """Initialize the fake note service."""
        self.received_user_id: UUID | None = None
        self.received_note_id: UUID | None = None
        self.call_count = 0

    async def delete_note(self, user_id: UUID, note_id: UUID) -> None:
        """Record the deletion call."""
        self.received_user_id = user_id
        self.received_note_id = note_id
        self.call_count += 1


def _build_tool() -> tuple[FakeNoteService, Any]:
    """Build the delete_note tool wired with a fake note service."""
    notes_service = FakeNoteService()
    tool = make_delete_note_tool(
        notes_service=cast(NoteService, notes_service),
        user_id=TEST_USER_ID,
    )
    return notes_service, tool


def test_tool_definition_has_expected_metadata() -> None:
    """Test that the tool definition exposes the expected name and schema."""
    _, tool = _build_tool()

    assert tool["name"] == "delete_note"
    assert tool["description"]
    assert tool["parameters"]["type"] == "object"
    assert callable(tool["handler"])
    assert set(tool["parameters"]["properties"]) == {"note_id"}
    assert tool["parameters"]["required"] == ["note_id"]


@pytest.mark.asyncio
async def test_handler_passes_identifiers_to_note_service() -> None:
    """Test that the handler forwards the user and note identifiers."""
    notes_service, tool = _build_tool()

    await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert notes_service.received_user_id == TEST_USER_ID
    assert notes_service.received_note_id == TEST_NOTE_ID
    assert notes_service.call_count == 1


@pytest.mark.asyncio
async def test_handler_returns_deletion_status() -> None:
    """Test that the handler reports a successful deletion result."""
    _, tool = _build_tool()

    result = await tool["handler"](note_id=str(TEST_NOTE_ID))

    assert result == {
        "status": "deleted",
        "note_id": str(TEST_NOTE_ID),
    }


@pytest.mark.asyncio
async def test_handler_rejects_invalid_note_id() -> None:
    """Test that a malformed note identifier raises a value error."""
    notes_service, tool = _build_tool()

    with pytest.raises(ValueError):
        await tool["handler"](note_id="not-a-uuid")

    assert notes_service.call_count == 0
