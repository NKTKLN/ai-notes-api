"""Database model mixins.

This module defines reusable SQLAlchemy ORM mixins for timestamp tracking
and soft deletion.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mixin that adds creation and update timestamps to a database model.

    Attributes:
        created_at (Mapped[datetime]): Date and time when the record was created.
        updated_at (Mapped[datetime]): Date and time when the record was last updated.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin that adds soft deletion support to a database model.

    Attributes:
        deleted_at (Mapped[datetime]): Date and time when the record was soft-deleted.
            If the value is None, the record is considered active.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
