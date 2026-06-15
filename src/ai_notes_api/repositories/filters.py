"""Repository filters module.

This module defines filter objects used by repositories to build database
queries.
"""

from dataclasses import dataclass

from ai_notes_api.db.models import MessageRole, ModelSource


@dataclass(slots=True, frozen=True)
class NoteListFilters:
    """Filters used to fetch a list of notes.

    Attributes:
        limit (int): Maximum number of notes to return.
        offset (int): Number of notes to skip before returning results.
        search (str | None): Optional text used to search notes by title or
            content.
        source (ModelSource | None): Optional note source used to filter
            results.
        tag (str | None): Optional tag used to filter results.
        model_name (str | None): Optional model name used to filter results.
    """

    limit: int = 20
    offset: int = 0
    search: str | None = None
    source: ModelSource | None = None
    tag: str | None = None
    model_name: str | None = None


@dataclass(slots=True, frozen=True)
class ChatSessionListFilters:
    """Filters used to fetch a list of chat sessions.

    Attributes:
        limit (int): Maximum number of chat sessions to return.
        offset (int): Number of chat sessions to skip before returning results.
        search (str | None): Optional text used to search chat sessions by title.
    """

    limit: int = 20
    offset: int = 0
    search: str | None = None


@dataclass(slots=True, frozen=True)
class MessageListFilters:
    """Filters used to fetch a list of messages.

    Attributes:
        limit (int): Maximum number of messages to return.
        offset (int): Number of messages to skip before returning results.
        search (str | None): Optional text used to search message content.
        role (MessageRole | None): Optional message role used to filter results.
        model_name (str | None): Optional model name used to filter results.
        provider (str | None): Optional AI provider name used to filter results.
    """

    limit: int = 20
    offset: int = 0
    search: str | None = None
    role: MessageRole | None = None
    model_name: str | None = None
    provider: str | None = None
