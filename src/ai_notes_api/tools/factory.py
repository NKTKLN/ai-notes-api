"""LLM tool registry builder module.

This module defines a factory for building an LLM tool registry with built-in tools.
"""

from uuid import UUID

from ai_notes_api.services.note import NoteService
from ai_notes_api.tools.builtins import (
    make_create_note_tool,
    make_delete_note_tool,
    make_get_note_by_id_tool,
    make_search_notes_tool,
    make_update_note_tool,
)
from ai_notes_api.tools.registry import ToolRegistry


def build_registry(notes_service: NoteService, user_id: UUID) -> ToolRegistry:
    """Build an LLM tool registry for a user.

    Args:
        notes_service (NoteService): Note service used by built-in tools.
        user_id (UUID): Unique identifier of the user whose tools are built.

    Returns:
        ToolRegistry: Configured LLM tool registry.
    """
    registry = ToolRegistry()

    notes_tools = [
        make_search_notes_tool,
        make_get_note_by_id_tool,
        make_create_note_tool,
        make_delete_note_tool,
        make_update_note_tool,
    ]

    for tool in notes_tools:
        registry.register(
            **tool(
                notes_service=notes_service,
                user_id=user_id,
            )
        )

    return registry
