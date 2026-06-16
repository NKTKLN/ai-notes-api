"""Memory summarizer module.

This module defines a service for updating chat memory summaries from recent
chat messages.
"""

from dataclasses import asdict

from openai import AsyncOpenAI

from ai_notes_api.core import settings
from ai_notes_api.llm.models import LLMMessage
from ai_notes_api.memory.prompts import SUMMARY_PROMPT


class MemorySummarizer:
    """Summarizer for chat memory.

    Args:
        client (AsyncOpenAI): Shared asynchronous OpenAI client.
    """

    def __init__(self, client: AsyncOpenAI) -> None:
        """Initialize the memory summarizer.

        Args:
            client (AsyncOpenAI): Shared asynchronous OpenAI client.
        """
        self.client = client

    async def summarize(
        self,
        summary: str,
        context_messages: list[LLMMessage],
    ) -> str:
        """Update a chat memory summary from context messages.

        Args:
            summary (str): Existing chat memory summary.
            context_messages (list[LLMMessage]): LLM messages used as context.

        Returns:
            str: Updated chat memory summary.
        """
        existing_summary = summary.strip() or "No previous summary."

        llm_messages = [
            LLMMessage(
                role="system",
                content=SUMMARY_PROMPT,
            ),
            LLMMessage(
                role="user",
                content=f"Existing summary:\n{existing_summary}",
            ),
            LLMMessage(
                role="user",
                content="Recent conversation messages follow.",
            ),
            *context_messages,
        ]

        response = await self.client.responses.create(
            input=[asdict(message) for message in llm_messages],
            model=settings.open_ai_model,
            temperature=0,
            max_output_tokens=500,
        )

        return response.output_text.strip()
