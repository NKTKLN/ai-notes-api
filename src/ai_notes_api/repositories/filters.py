"""Repository filters module.

This module defines filter objects used by repositories to build database
queries.
"""

from dataclasses import dataclass

from ai_notes_api.db.models import ModelSource


@dataclass(slots=True, frozen=True)
class NoteListFilters:
    """Filters used to fetch a list of notes.

    Attributes:
        limit (int): Maximum number of notes to return.
        offset (int): Number of notes to skip before returning results.
        search (str | None): Optional text used to search notes by title or content.
        source (ModelSource | None): Optional note source used to filter results.
        tag (str | None): Optional tag used to filter results.
        model_name (str | None): Optional model name used to filter results.
    """

    limit: int = (20,)
    offset: int = (0,)
    search: str | None = None
    source: ModelSource | None = None
    tag: str | None = None
    model_name: str | None = None
