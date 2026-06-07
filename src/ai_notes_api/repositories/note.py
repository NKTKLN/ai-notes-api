"""Note repository module.

This module provides a repository for creating, reading, updating, and
soft-deleting notes in the database.
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_notes_api.db.models import Note
from ai_notes_api.repositories.filters import NoteListFilters


class NoteRepository:
    """Repository for note database operations.

    Args:
        session (AsyncSession): Asynchronous SQLAlchemy session used to execute
            database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the note repository.

        Args:
            session (AsyncSession): Asynchronous SQLAlchemy session used by the
                repository.
        """
        self.session = session

    async def create(self, note: Note) -> Note:
        """Create a note in the database.

        Args:
            note (Note): Note instance to persist.

        Returns:
            Note: Persisted note with refreshed database-generated fields.
        """
        self.session.add(note)

        await self.session.flush()
        await self.session.refresh(note)

        logger.info("Note created: id={}", note.id)

        return note

    async def get_by_id(self, note_id: int) -> Note | None:
        """Return a note by its identifier.

        Args:
            note_id (int): Unique note identifier.

        Returns:
            Note | None: Matching note if found and not soft-deleted; otherwise, None.
        """
        stmt = select(Note).where(Note.id == note_id).where(Note.deleted_at.is_(None))

        result = await self.session.execute(stmt)
        note = result.scalar_one_or_none()

        if note is None:
            logger.debug("Note not found: id={}", note_id)
        else:
            logger.debug("Note found: id={}", note_id)

        return note

    async def get_list(
        self,
        limit: int = 20,
        offset: int = 0,
        filters: NoteListFilters | None = None,
    ) -> list[Note]:
        """Return a paginated list of notes.

        Args:
            limit (int): Maximum number of notes to return.
            offset (int): Number of notes to skip before returning results.
            filters (NoteListFilters | None): Optional filters used to narrow the
                result set.

        Returns:
            list[Note]: List of matching non-deleted notes ordered by creation
            date in descending order.
        """
        stmt = select(Note).where(Note.deleted_at.is_(None))

        if filters.source is not None:
            stmt = stmt.where(Note.source == filters.source)

        if filters.tag is not None:
            stmt = stmt.where(Note.tags.contains([filters.tag]))

        if filters.model_name is not None:
            stmt = stmt.where(Note.model_name == filters.model_name)

        search = filters.search.strip()
        if search is not None:
            search_value = f"%{search}%"

            stmt = stmt.where(
                or_(
                    Note.title.ilike(search_value),
                    Note.content.ilike(search_value),
                )
            )

        stmt = stmt.order_by(Note.created_at.desc()).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        notes = list(result.scalars().all())

        logger.debug(
            (
                "Notes list fetched: count={}, limit={}, offset={}, "
                "source={}, tag={}, model_name={}, search={}"
            ),
            len(notes),
            limit,
            offset,
            filters.source,
            filters.tag,
            filters.model_name,
            filters.search,
        )

        return notes

    async def update(self, note: Note) -> Note:
        """Update an existing note in the database.

        Args:
            note (Note): Note instance with updated field values.

        Returns:
            Note: Updated and refreshed note instance.
        """
        await self.session.flush()
        await self.session.refresh(note)

        logger.info("Note updated: id={}", note.id)

        return note

    async def soft_delete(self, note: Note) -> None:
        """Soft-delete a note.

        Sets the note deletion timestamp instead of removing the row from the database.

        Args:
            note (Note): Note instance to soft-delete.
        """
        note.deleted_at = datetime.now(UTC)

        await self.session.flush()

        logger.info("Note soft-deleted: id={}", note.id)
