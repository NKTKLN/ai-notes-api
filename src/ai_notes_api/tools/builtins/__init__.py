"""Built-in LLM tools package.

This package exports built-in LLM tool factories.
"""

from .search_notes import make_search_notes_tool

__all__ = ["make_search_notes_tool"]
