"""Message repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting messages in the database.
"""

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update

from ai_notes_api.db.models import ChatSession, Message
from ai_notes_api.repositories.base import BaseRepository
from ai_notes_api.repositories.filters import MessageListFilters


class MessageRepository(BaseRepository):
    """Repository for message database operations."""

    async def create(self, message: Message) -> Message:
        """Create a message in the database.

        Args:
            message (Message): Message instance to persist.

        Returns:
            Message: Persisted message with refreshed database-generated fields.
        """
        self.session.add(message)

        await self.session.flush()
        await self.session.refresh(message)

        logger.info("Message created: id={}", message.id)

        return message

    async def get_by_id(self, message_id: UUID) -> Message | None:
        """Return a message by its identifier.

        Args:
            message_id (UUID): Unique message identifier.

        Returns:
            Message | None: Matching message if found and not soft-deleted;
            otherwise, None.
        """
        stmt = (
            select(Message)
            .where(Message.id == message_id)
            .where(Message.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if message is None:
            logger.debug("Message not found: id={}", message_id)
        else:
            logger.debug("Message found: id={}", message_id)

        return message

    async def get_by_id_for_user(
        self,
        user_id: UUID,
        message_id: UUID,
    ) -> Message | None:
        """Return a user's message by its identifier.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            message_id (UUID): Unique message identifier.

        Returns:
            Message | None: Matching message if found and not soft-deleted;
            otherwise, None.
        """
        stmt = (
            select(Message)
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .where(Message.id == message_id)
            .where(Message.deleted_at.is_(None))
        )

        result = await self.session.execute(stmt)
        message = result.scalar_one_or_none()

        if message is None:
            logger.debug("Message not found: id={}", message_id)
        else:
            logger.debug("Message found: id={}", message_id)

        return message

    async def get_list(
        self,
        user_id: UUID,
        session_id: UUID,
        filters: MessageListFilters,
    ) -> list[Message]:
        """Return a paginated list of messages.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            filters (MessageListFilters): Filters used to narrow the result set.

        Returns:
            list[Message]: List of matching non-deleted messages ordered by
            creation date in descending order.
        """
        stmt = (
            select(Message)
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .where(Message.session_id == session_id)
            .where(Message.deleted_at.is_(None))
        )

        if filters.provider is not None:
            stmt = stmt.where(Message.provider == filters.provider)

        if filters.model_name is not None:
            stmt = stmt.where(Message.model_name == filters.model_name)

        if filters.role is not None:
            stmt = stmt.where(Message.role == filters.role)

        if filters.search is not None:
            search = filters.search.strip()

            if search:
                search_value = f"%{search}%"
                stmt = stmt.where(Message.content.ilike(search_value))

        stmt = (
            stmt.order_by(Message.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )

        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())

        logger.debug(
            (
                "Messages list fetched: count={}, user_id={}, session_id={}, "
                "limit={}, offset={}, provider={}, model_name={}, role={}, "
                "search={}"
            ),
            len(messages),
            user_id,
            session_id,
            filters.limit,
            filters.offset,
            filters.provider,
            filters.model_name,
            filters.role,
            filters.search,
        )

        return messages

    async def get_last_messages(
        self,
        user_id: UUID,
        session_id: UUID,
        limit: int,
    ) -> list[Message]:
        """Return the latest messages from a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            limit (int): Maximum number of latest messages to return.

        Returns:
            list[Message]: List of latest non-deleted messages ordered by creation
            date in descending order.
        """
        stmt = (
            select(Message)
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .where(Message.session_id == session_id)
            .where(Message.deleted_at.is_(None))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())

        logger.debug(
            "Latest messages fetched: count={}, user_id={}, session_id={}, limit={}",
            len(messages),
            user_id,
            session_id,
            limit,
        )

        return messages

    async def get_messages_after(
        self,
        user_id: UUID,
        session_id: UUID,
        message_id: UUID | None,
        limit: int | None = None,
    ) -> list[Message]:
        """Return messages created after a specific message in a chat session.

        Args:
            user_id (UUID): Unique identifier of the user who owns the chat session.
            session_id (UUID): Unique chat session identifier.
            message_id (UUID | None): Unique identifier of the message used as the
                starting point. If None, messages are returned without this filter.
            limit (int | None): Optional maximum number of messages to return.

        Returns:
            list[Message]: List of matching non-deleted messages created after the
                given message, ordered by creation date in descending order.
        """
        stmt = (
            select(Message)
            .join(ChatSession, ChatSession.id == Message.session_id)
            .where(ChatSession.user_id == user_id)
            .where(Message.session_id == session_id)
            .where(Message.deleted_at.is_(None))
            .order_by(Message.created_at.desc())
        )

        if message_id is not None:
            subquery = (
                select(Message.created_at)
                .where(Message.id == message_id)
                .scalar_subquery()
            )

            stmt = stmt.where(Message.created_at > subquery)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())

        logger.debug(
            "Messages after checkpoint fetched: count={}, user_id={}, session_id={}, "
            "message_id={}, limit={}",
            len(messages),
            user_id,
            session_id,
            message_id,
            limit,
        )

        return messages

    async def update(self, message: Message) -> Message:
        """Update an existing message in the database.

        Args:
            message (Message): Message instance with updated field values.

        Returns:
            Message: Updated and refreshed message instance.
        """
        await self.session.flush()
        await self.session.refresh(message)

        logger.info("Message updated: id={}", message.id)

        return message

    async def soft_delete(self, message: Message) -> None:
        """Soft-delete a message and following messages in the same session.

        Sets the deletion timestamp for the given message and all later messages
        in the same chat session instead of removing rows from the database.

        Args:
            message (Message): Message instance to soft-delete.
        """
        now = datetime.now(UTC)

        message.deleted_at = now

        await self.session.execute(
            update(Message)
            .where(Message.session_id == message.session_id)
            .where(Message.deleted_at.is_(None))
            .where(Message.created_at > message.created_at)
            .values(deleted_at=now)
        )

        await self.session.flush()

        logger.info("Message and following messages soft-deleted: id={}", message.id)
