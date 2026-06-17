"""Chat memory database model module.

This module defines the SQLAlchemy ORM model for chat memory records.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession


class ChatMemory(Base, TimestampMixin):
    """SQLAlchemy ORM model representing chat memory.

    Attributes:
        id (Mapped[UUID]): Unique chat memory identifier.
        session_id (Mapped[UUID]): Identifier of the chat session associated
            with the chat memory.
        chat_session (Mapped[ChatSession]): Chat session associated with the
            chat memory.
        summary (Mapped[str]): Summary of the chat session memory.
        facts (Mapped[list[dict[str, Any]]]): Facts extracted from the chat session.
    """

    __tablename__ = "chat_memories"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    session_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE",
        ),
        unique=True,
        nullable=False,
        index=True,
    )

    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="memory",
    )

    summary: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )

    facts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
