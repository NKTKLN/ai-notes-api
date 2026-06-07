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
        search: Optional text used to search notes by title or content.
        source: Optional note source used to filter results.
        tag: Optional tag used to filter results.
        model_name: Optional model name used to filter results.
    """

    search: str | None = None
    source: ModelSource | None = None
    tag: str | None = None
    model_name: str | None = None
