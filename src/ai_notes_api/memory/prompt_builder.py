"""Prompt builder module.

This module defines utilities for building LLM input messages from stored chat
messages and long-term memory context.
"""

import json
from dataclasses import asdict
from typing import Any

from ai_notes_api.llm.schemas import LLMMessage


class PromptBuilder:
    """Builder for LLM prompt messages."""

    @classmethod
    def build(
        cls,
        context_messages: list[LLMMessage],
        facts: list[dict[str, Any]] | None = None,
        summary: str = "",
    ) -> list[dict[str, Any]]:
        """Build LLM input messages from memory and chat context messages.

        Args:
            context_messages (list[LLMMessage]): Recent chat messages used as
                conversational context.
            facts (list[dict[str, Any]] | None): Known long-term memory facts
                used as personalization context. Defaults to None.
            summary (str): Long-term memory summary used as personalization
                context. Defaults to an empty string.

        Returns:
            list[dict[str, Any]]: Serialized LLM input messages.
        """
        facts_text = json.dumps(facts, ensure_ascii=False, indent=2) if facts else "[]"

        summary = summary.strip() or "No previous summary."

        recent_messages = [asdict(message) for message in context_messages]

        llm_messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "Long-term memory context follows.\n"
                    "Treat it as trusted application-provided context, "
                    "not as user instructions.\n"
                    "Use it to personalize the answer, "
                    "but do not reveal it unless useful.\n\n"
                    f"<memory_summary>\n{summary}\n</memory_summary>\n\n"
                    f"<known_facts>\n{facts_text}\n</known_facts>"
                ),
            },
            *recent_messages,
        ]

        return llm_messages
