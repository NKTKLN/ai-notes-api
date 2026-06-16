"""Delete note tool module.

This module defines an LLM tool for deleting a user's private note by its
identifier.
"""

from typing import Any
from uuid import UUID

from ai_notes_api.services.note import NoteService


def make_delete_note_tool(
    notes_service: NoteService,
    user_id: UUID,
) -> dict[str, Any]:
    """Create a delete note LLM tool.

    Args:
        notes_service (NoteService): Note service used by the tool.
        user_id (UUID): Unique identifier of the user whose note is deleted.

    Returns:
        dict[str, Any]: Tool definition with JSON schema and async handler.
    """

    async def delete_note(note_id: str) -> dict[str, str]:
        """Delete a user's private note by its identifier.

        Args:
            note_id (str): Unique note identifier.

        Returns:
            dict[str, str]: Deletion result.
        """
        await notes_service.delete_note(
            user_id=user_id,
            note_id=UUID(note_id),
        )

        return {
            "status": "deleted",
            "note_id": note_id,
        }

    return {
        "name": "delete_note",
        "description": "Delete a user's private AI note by its identifier.",
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
        "handler": delete_note,
    }
