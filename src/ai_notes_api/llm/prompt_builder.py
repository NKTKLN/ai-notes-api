"""Prompt builder module.

This module defines utilities for building LLM input messages from stored chat
messages.
"""

from dataclasses import asdict
from typing import Any, ClassVar

from ai_notes_api.db.models import Message, MessageRole
from ai_notes_api.llm.models import LLMMessage


class PromptBuilder:
    """Builder for LLM prompt messages.

    Attributes:
        SYSTEM_PROMPT (ClassVar[str]): System prompt prepended to chat context.
    """

    SYSTEM_PROMPT: ClassVar[str] = (
        "Отвечай на языке пользователя. Не выдумывай факты о пользователе. "
        # "Используй долгосрочную память только если она релевантна вопросу.\n"
        # "Использование инструментов работы с заметками строго по чёткому "
        # "запросу пользователя.\n"
        # "Не выдумывай факты из документов: если данных нет, так и скажи.\n"
    )

    @classmethod
    def build(cls, context_messages: list[Message]) -> list[dict[str, Any]]:
        """Build LLM input messages from chat context messages.

        Args:
            context_messages (list[Message]): Chat messages used as context.

        Returns:
            list[dict[str, Any]]: Serialized LLM input messages.
        """
        llm_messages = [
            LLMMessage(
                role=MessageRole.SYSTEM,
                content=cls.SYSTEM_PROMPT,
            )
        ]

        for message in context_messages:
            llm_messages.append(
                LLMMessage(
                    role=message.role,
                    content=message.content,
                )
            )

        return [asdict(message) for message in llm_messages]
