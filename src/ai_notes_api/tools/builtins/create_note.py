"""Create note tool module.

This module defines an LLM tool for creating a user's private note.
"""

from typing import Any
from uuid import UUID

from ai_notes_api.db.models import ModelSource
from ai_notes_api.schemas import NoteCreateSchema
from ai_notes_api.services.note import NoteService


def make_create_note_tool(
    notes_service: NoteService,
    user_id: UUID,
) -> dict[str, Any]:
    """Create a create note LLM tool.

    Args:
        notes_service (NoteService): Note service used by the tool.
        user_id (UUID): Unique identifier of the user whose note is created.

    Returns:
        dict[str, Any]: Tool definition with JSON schema and async handler.
    """

    async def create_note(
        title: str,
        content: str = "",
        tags: list[str] | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Create a user's private note.

        Args:
            title (str): Note title.
            content (str): Main note content.
            tags (list[str] | None): Optional list of note tags.
            model_name (str | None): Optional name of the model associated with
                the note.

        Returns:
            dict[str, Any]: Created note serialized for the LLM.
        """
        note = await notes_service.create_note(
            user_id=user_id,
            data=NoteCreateSchema(
                title=title,
                content=content,
                tags=tags or [],
                source=ModelSource.LLM,
                model_name=model_name,
            ),
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
        "name": "create_note",
        "description": "Create a private AI note for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Note title.",
                },
                "content": {
                    "type": "string",
                    "description": "Main note content.",
                    "default": "",
                },
                "tags": {
                    "type": ["array", "null"],
                    "description": "Optional list of note tags.",
                    "items": {
                        "type": "string",
                    },
                    "default": None,
                },
                "model_name": {
                    "type": ["string", "null"],
                    "description": "Optional model name associated with the note.",
                    "default": None,
                },
            },
            "required": ["title"],
            "additionalProperties": False,
        },
        "handler": create_note,
    }
