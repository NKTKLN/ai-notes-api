"""RAG query repository module.

This module provides a repository for creating, reading, and updating RAG
queries in the database.
"""

from uuid import UUID

from loguru import logger
from sqlalchemy import select

from ai_notes_api.db.models import RagQuery
from ai_notes_api.repositories.base import BaseRepository


class RagQueryRepository(BaseRepository):
    """Repository for RAG query database operations."""

    async def create(self, rag_query: RagQuery) -> RagQuery:
        """Create a RAG query in the database.

        Args:
            rag_query (RagQuery): RAG query instance to persist.

        Returns:
            RagQuery: Persisted RAG query with refreshed database-generated
            fields.
        """
        self.session.add(rag_query)

        await self.session.flush()
        await self.session.refresh(rag_query)

        logger.info("RAG query created: id={}", rag_query.id)

        return rag_query

    async def get_by_id(self, query_id: UUID) -> RagQuery | None:
        """Return a RAG query by its identifier.

        Args:
            query_id (UUID): Unique RAG query identifier.

        Returns:
            RagQuery | None: Matching RAG query if found; otherwise, None.
        """
        stmt = select(RagQuery).where(RagQuery.id == query_id)

        result = await self.session.execute(stmt)
        rag_query = result.scalar_one_or_none()

        if rag_query is None:
            logger.debug("RAG query not found: id={}", query_id)
        else:
            logger.debug("RAG query found: id={}", query_id)

        return rag_query

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        query_id: UUID,
    ) -> RagQuery | None:
        """Return a user's RAG query by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the RAG query.
            query_id (UUID): Unique RAG query identifier.

        Returns:
            RagQuery | None: Matching RAG query if found; otherwise, None.
        """
        stmt = (
            select(RagQuery)
            .where(RagQuery.user_id == user_id)
            .where(RagQuery.id == query_id)
        )

        result = await self.session.execute(stmt)
        rag_query = result.scalar_one_or_none()

        if rag_query is None:
            logger.debug("RAG query not found: id={}", query_id)
        else:
            logger.debug("RAG query found: id={}", query_id)

        return rag_query

    async def get_list_for_session(
        self,
        user_id: UUID,
        session_id: UUID,
    ) -> list[RagQuery]:
        """Return a user's RAG queries for a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the RAG queries.
            session_id (UUID): Unique chat session identifier.

        Returns:
            list[RagQuery]: List of matching RAG queries ordered by creation date
            in descending order.
        """
        stmt = (
            select(RagQuery)
            .where(RagQuery.user_id == user_id)
            .where(RagQuery.session_id == session_id)
            .order_by(RagQuery.created_at.desc())
        )

        result = await self.session.execute(stmt)
        rag_queries = list(result.scalars().all())

        logger.debug(
            "RAG queries list fetched: count={}, user_id={}, session_id={}",
            len(rag_queries),
            user_id,
            session_id,
        )

        return rag_queries

    async def update(self, rag_query: RagQuery) -> RagQuery:
        """Update an existing RAG query in the database.

        Args:
            rag_query (RagQuery): RAG query instance with updated field values.

        Returns:
            RagQuery: Updated and refreshed RAG query instance.
        """
        await self.session.flush()
        await self.session.refresh(rag_query)

        logger.info("RAG query updated: id={}", rag_query.id)

        return rag_query
