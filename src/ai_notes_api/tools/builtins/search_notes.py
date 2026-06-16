"""Search notes tool module.

This module defines an LLM tool for searching a user's private notes.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import ModelSource
from ai_notes_api.repositories import NoteListFilters, NoteRepository


def make_search_notes_tool(session: AsyncSession, user_id: UUID) -> dict[str, Any]:
    """Create a search notes LLM tool.

    Args:
        session (AsyncSession): Asynchronous database session used by the tool.
        user_id (UUID): Unique identifier of the user whose notes are searched.

    Returns:
        dict[str, Any]: Tool definition with JSON schema and async handler.
    """

    async def search_notes(  # noqa: PLR0913
        limit: int = 5,
        offset: int = 0,
        search: str | None = None,
        source: ModelSource | None = None,
        tag: str | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Search a user's private notes.

        Args:
            limit (int): Maximum number of notes to return.
            offset (int): Number of notes to skip before returning results.
            search (str | None): Optional text used to search notes by title or
                content.
            source (ModelSource | None): Optional note source used to filter
                results.
            tag (str | None): Optional tag used to filter results.
            model_name (str | None): Optional model name used to filter results.

        Returns:
            dict[str, Any]: Matching notes serialized for the LLM.
        """
        repository = NoteRepository(session)

        source_value = ModelSource(source) if isinstance(source, str) else source

        notes = await repository.get_list(
            user_id=user_id,
            filters=NoteListFilters(
                limit=limit,
                offset=offset,
                search=search,
                source=source_value,
                tag=tag,
                model_name=model_name,
            ),
        )

        return {
            "items": [
                {
                    "id": str(note.id),
                    "title": note.title,
                    "content": note.content[:1000],
                    "tags": note.tags,
                    "source": note.source.value,
                    "model_name": note.model_name,
                    "created_at": note.created_at.isoformat(),
                }
                for note in notes
            ]
        }

    return {
        "name": "search_notes",
        "description": "Search user's private AI notes by text query.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of notes to return.",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 15,
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of notes to skip before returning.",
                    "default": 0,
                    "minimum": 0,
                },
                "search": {
                    "type": ["string", "null"],
                    "description": "Text used to search notes by title or content.",
                    "default": None,
                },
                "source": {
                    "type": ["string", "null"],
                    "enum": ["manual", "llm", "import", "api", None],
                    "description": "Optional filter by note source.",
                    "default": None,
                },
                "tag": {
                    "type": ["string", "null"],
                    "description": "Optional filter by tag.",
                    "default": None,
                },
                "model_name": {
                    "type": ["string", "null"],
                    "description": "Optional filter by model name.",
                    "default": None,
                },
            },
            "required": [],
            "additionalProperties": False,
        },
        "handler": search_notes,
    }
