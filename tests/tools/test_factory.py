"""Tests for the LLM tool registry factory."""

from typing import Any, cast
from uuid import UUID

from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.factory import build_registry
from ai_notes_api.tools.registry import ToolRegistry

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeNoteService:
    """Fake note service used to build the tool registry."""

    async def get_notes_list(
        self,
        user_id: UUID,  # noqa: ARG002
        filters: Any,  # noqa: ARG002
    ) -> list[Any]:
        """Return an empty note list."""
        return []


def test_build_registry_returns_registry_with_search_notes() -> None:
    """Test that the built registry exposes the search_notes tool."""
    registry = build_registry(
        notes_service=cast(NoteService, FakeNoteService()),
        user_id=TEST_USER_ID,
    )

    assert isinstance(registry, ToolRegistry)

    tools = registry.get_tools()
    names = [tool["name"] for tool in tools]

    assert "search_notes" in names


def test_build_registry_creates_independent_registries() -> None:
    """Test that each call returns a separate registry instance."""
    notes = cast(NoteService, FakeNoteService())

    first = build_registry(notes_service=notes, user_id=TEST_USER_ID)
    second = build_registry(notes_service=notes, user_id=TEST_USER_ID)

    assert first is not second
