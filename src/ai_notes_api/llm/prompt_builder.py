"""Prompt builder module.

This module defines utilities for building LLM input messages from stored chat
messages.
"""

from dataclasses import asdict
from typing import Any, ClassVar

from ai_notes_api.db.models import MessageRole
from ai_notes_api.llm.models import LLMMessage


class PromptBuilder:
    """Builder for LLM prompt messages.

    Attributes:
        SYSTEM_PROMPT (ClassVar[str]): System prompt prepended to the chat context.
    """

    SYSTEM_PROMPT: ClassVar[str] = (
        "Respond in the user's language. Do not invent facts about the user. "
        "Use note-management tools only when the user clearly asks for it."
        # "Use long-term memory only when it is relevant to the question.\n"
        # "Do not invent facts from documents: if data is missing, say so.\n"
    )

    @classmethod
    def build(cls, context_messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Build LLM input messages from chat context messages.

        Args:
            context_messages (list[LLMMessage]): Chat messages used as context.

        Returns:
            list[dict[str, Any]]: Serialized LLM input messages.
        """
        llm_messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content=cls.SYSTEM_PROMPT,
            ),
            LLMMessage(
                role=MessageRole.USER,
                content="Recent conversation messages follow.",
            ),
            *context_messages,
        ]

        return [asdict(message) for message in llm_messages]
