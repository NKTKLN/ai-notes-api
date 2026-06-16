"""Integrations package.

This package exports shared third-party integration clients.
"""

from ai_notes_api.integrations.openai import close_openai_client, openai_client

__all__ = ["openai_client", "close_openai_client"]
