"""Message database model module.

This module defines the SQLAlchemy ORM model for chat messages.
"""

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_notes_api.db.models.base import Base
from ai_notes_api.db.models.datetime import TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from ai_notes_api.db.models.chat_session import ChatSession


class MessageRole(StrEnum):
    """Available chat message roles.

    Attributes:
        SYSTEM (str): System message role.
        USER (str): User message role.
        ASSISTANT (str): Assistant message role.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(Base, TimestampMixin, SoftDeleteMixin):
    """SQLAlchemy ORM model representing a chat message.

    Attributes:
        id (Mapped[UUID]): Unique message identifier.
        session_id (Mapped[UUID]): Identifier of the chat session that owns the message.
        chat_session (Mapped[ChatSession]): Chat session that owns the message.
        content (Mapped[str]): Message content.
        role (Mapped[MessageRole]): Role of the message author.
        provider (Mapped[str | None]): Optional AI provider name.
        model_name (Mapped[str | None]): Optional AI model name.
        prompt_tokens (Mapped[int | None]): Optional number of prompt tokens.
        completion_tokens (Mapped[int | None]): Optional number of completion tokens.
        total_tokens (Mapped[int | None]): Optional total number of tokens.
    """

    __tablename__ = "messages"

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
        nullable=False,
        index=True,
    )

    chat_session: Mapped["ChatSession"] = relationship(
        back_populates="messages",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    role: Mapped[MessageRole] = mapped_column(
        SqlEnum(
            MessageRole,
            name="message_role",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )

    provider: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    prompt_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    completion_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    total_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )
