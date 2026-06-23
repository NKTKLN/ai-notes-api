"""RAG query source repository module.

This module provides a repository for creating and reading RAG query sources in
the database.
"""

from collections.abc import Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import RagQuerySource
from ai_notes_api.repositories.base import BaseRepository


class RagQuerySourceRepository(BaseRepository):
    """Repository for RAG query source database operations."""

    async def create(self, rag_query_source: RagQuerySource) -> RagQuerySource:
        """Create a RAG query source in the database.

        Args:
            rag_query_source (RagQuerySource): RAG query source instance to
                persist.

        Returns:
            RagQuerySource: Persisted RAG query source with refreshed
            database-generated fields.
        """
        self.session.add(rag_query_source)

        await self.session.flush()
        await self.session.refresh(rag_query_source)

        logger.info("RAG query source created: id={}", rag_query_source.id)

        return rag_query_source

    async def create_many(
        self,
        rag_query_sources: Sequence[RagQuerySource],
    ) -> list[RagQuerySource]:
        """Create multiple RAG query sources in the database.

        Args:
            rag_query_sources (Sequence[RagQuerySource]): RAG query source
                instances to persist.

        Returns:
            list[RagQuerySource]: Persisted RAG query sources with refreshed
            database-generated fields.
        """
        rag_query_sources = list(rag_query_sources)

        self.session.add_all(rag_query_sources)

        await self.session.flush()

        for rag_query_source in rag_query_sources:
            await self.session.refresh(rag_query_source)

        logger.info("RAG query sources created: count={}", len(rag_query_sources))

        return rag_query_sources

    async def get_list_for_rag_query(
        self,
        rag_query_id: UUID,
    ) -> list[RagQuerySource]:
        """Return RAG query sources for a RAG query.

        Args:
            rag_query_id (UUID): Unique RAG query identifier.

        Returns:
            list[RagQuerySource]: List of matching RAG query sources ordered by
            rank in ascending order.
        """
        stmt = (
            select(RagQuerySource)
            .where(RagQuerySource.rag_query_id == rag_query_id)
            .order_by(RagQuerySource.rank.asc())
        )

        result = await self.session.execute(stmt)
        rag_query_sources = list(result.scalars().all())

        logger.debug(
            "RAG query sources list fetched: count={}, rag_query_id={}",
            len(rag_query_sources),
            rag_query_id,
        )

        return rag_query_sources
