"""Create notes table.

Revision ID: 3dd76b22c38f
Revises:
Create Date: 2026-05-30 18:21:12.109072
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "3dd76b22c38f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


model_source_enum = postgresql.ENUM(
    "manual",
    "llm",
    "import",
    "api",
    name="model_source",
    create_type=False,
)


def upgrade() -> None:
    """Create the notes table."""
    model_source_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("source", model_source_enum, nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "model_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop the notes table."""
    op.drop_table("notes")
    model_source_enum.drop(op.get_bind(), checkfirst=True)
