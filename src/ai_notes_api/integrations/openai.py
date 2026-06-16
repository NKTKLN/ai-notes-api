"""OpenAI client module.

This module defines a shared asynchronous OpenAI client configured from
application settings.
"""

from loguru import logger
from openai import AsyncOpenAI

from ai_notes_api.core import settings

openai_client = AsyncOpenAI(
    api_key=settings.open_ai_api_key,
    base_url=settings.open_ai_api_url,
)


async def close_openai_client() -> None:
    """Close the shared asynchronous OpenAI client."""
    await openai_client.close()
    logger.debug("Async OpenAI client closed")
