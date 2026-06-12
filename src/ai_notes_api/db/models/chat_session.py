"""Chat session database model module.

This module defines the SQLAlchemy ORM model for chat sessions.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.message import Message
    from ai_notes_api.db.models.user import User


class ChatSession(Base, TimestampMixin, SoftDeleteMixin):
    """SQLAlchemy ORM model representing a chat session.

    Attributes:
        id (Mapped[UUID]): Unique chat session identifier.
        user_id (Mapped[UUID]): Identifier of the user who owns the chat session.
        user (Mapped[User]): User who owns the chat session.
        title (Mapped[str]): Chat session title.
        messages (Mapped[list[Message]]): Messages that belong to the chat session.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="chat_sessions",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
    )
