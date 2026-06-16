"""OpenAI embedding client module.

This module provides an OpenAI-backed client for creating embedding vectors.
"""

from loguru import logger
from openai import AsyncOpenAI

from ai_notes_api.core import settings


class EmbeddingClient:
    """Embedding client backed by the OpenAI API.

    Args:
        client (AsyncOpenAI): Shared asynchronous OpenAI client.
    """

    def __init__(self, client: AsyncOpenAI) -> None:
        """Initialize the embedding client.

        Args:
            client (AsyncOpenAI): Shared asynchronous OpenAI client.
        """
        self.client = client

    async def create_embedding(self, texts: list[str]) -> list[list[float]]:
        """Create embedding vectors for the given texts.

        Args:
            texts (list[str]): Texts to embed.

        Returns:
            list[list[float]]: Embedding vector for each input text, or an empty
            list if no texts are provided.
        """
        if not texts:
            logger.debug("No texts provided for embedding; returning empty list")
            return []

        logger.debug(
            "Creating embeddings: count={}, model={}",
            len(texts),
            settings.open_ai_embedding_model,
        )

        response = await self.client.embeddings.create(
            model=settings.open_ai_embedding_model,
            input=texts,
            encoding_format="float",
        )

        logger.info("Embeddings created: count={}", len(response.data))

        return [item.embedding for item in response.data]
