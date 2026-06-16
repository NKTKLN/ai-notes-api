"""LLM tool registry builder module.

This module defines a factory for building an LLM tool registry with built-in tools.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.tools.builtins import make_search_notes_tool
from ai_notes_api.tools.registry import ToolRegistry


def build_registry(session: AsyncSession, user_id: UUID) -> ToolRegistry:
    """Build an LLM tool registry for a user.

    Args:
        session (AsyncSession): Asynchronous database session used by tools.
        user_id (UUID): Unique identifier of the user whose tools are built.

    Returns:
        ToolRegistry: Configured LLM tool registry.
    """
    registry = ToolRegistry()

    registry.register(
        **make_search_notes_tool(
            session=session,
            user_id=user_id,
        )
    )

    return registry
