"""Update note tool module.

This module defines an LLM tool for updating a user's private note.
"""

from typing import Any
from uuid import UUID

from ai_notes_api.db.models import ModelSource
from ai_notes_api.schemas import NoteUpdateSchema
from ai_notes_api.services.note import NoteService


def make_update_note_tool(
    notes_service: NoteService,
    user_id: UUID,
) -> dict[str, Any]:
    """Create an update note LLM tool.

    Args:
        notes_service (NoteService): Note service used by the tool.
        user_id (UUID): Unique identifier of the user whose note is updated.

    Returns:
        dict[str, Any]: Tool definition with JSON schema and async handler.
    """

    async def update_note(  # noqa: PLR0913
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Update a user's private note.

        Args:
            note_id (str): Unique note identifier.
            title (str | None): Optional note title.
            content (str | None): Optional main note content.
            tags (list[str] | None): Optional list of note tags.
            source (str | None): Optional source that indicates how the note was
                created.
            model_name (str | None): Optional model name associated with the note.

        Returns:
            dict[str, Any]: Updated note serialized for the LLM.
        """
        source_value = ModelSource(source) if source is not None else None

        note = await notes_service.update_note(
            user_id=user_id,
            note_id=UUID(note_id),
            note_update=NoteUpdateSchema(
                title=title,
                content=content,
                tags=tags,
                source=source_value,
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
        "name": "update_note",
        "description": "Update a user's private AI note.",
        "parameters": {
            "type": "object",
            "properties": {
                "note_id": {
                    "type": "string",
                    "description": "Unique note identifier.",
                },
                "title": {
                    "type": ["string", "null"],
                    "description": "Optional note title.",
                    "default": None,
                },
                "content": {
                    "type": ["string", "null"],
                    "description": "Optional main note content.",
                    "default": None,
                },
                "tags": {
                    "type": ["array", "null"],
                    "description": "Optional list of note tags.",
                    "items": {
                        "type": "string",
                    },
                    "default": None,
                },
                "source": {
                    "type": ["string", "null"],
                    "enum": ["manual", "llm", "import", "api", None],
                    "description": "Optional note source.",
                    "default": None,
                },
                "model_name": {
                    "type": ["string", "null"],
                    "description": "Optional model name associated with the note.",
                    "default": None,
                },
            },
            "required": ["note_id"],
            "additionalProperties": False,
        },
        "handler": update_note,
    }
