"""Get note by ID tool module.

This module defines an LLM tool for retrieving a user's private note by its
identifier.
"""

from typing import Any
from uuid import UUID

from ai_notes_api.services.note import NoteService


def make_get_note_by_id_tool(
    notes_service: NoteService,
    user_id: UUID,
) -> dict[str, Any]:
    """Create a get note by ID LLM tool.

    Args:
        notes_service (NoteService): Note service used by the tool.
        user_id (UUID): Unique identifier of the user whose note is retrieved.

    Returns:
        dict[str, Any]: Tool definition with JSON schema and async handler.
    """

    async def get_note_by_id(note_id: str) -> dict[str, Any]:
        """Return a user's private note by its identifier.

        Args:
            note_id (str): Unique note identifier.

        Returns:
            dict[str, Any]: Matching note serialized for the LLM.
        """
        note = await notes_service.get_note(
            user_id=user_id,
            note_id=UUID(note_id),
        )

        return {
            "id": str(note.id),
            "title": note.title,
            "content": note.content[:1000],
            "tags": note.tags,
            "source": note.source.value,
            "model_name": note.model_name,
            "created_at": note.created_at.isoformat(),
        }

    return {
        "name": "get_note_by_id",
        "description": "Retrieve a user's private AI note by its identifier.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "Unique note identifier.",
                },
            },
            "required": ["note_id"],
            "additionalProperties": False,
        },
        "handler": get_note_by_id,
    }
