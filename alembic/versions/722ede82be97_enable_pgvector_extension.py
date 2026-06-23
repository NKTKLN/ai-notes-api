"""'Enable pgvector extension'

Revision ID: 722ede82be97
Revises: 683f77be6a55
Create Date: 2026-06-23 05:21:20.142401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '722ede82be97'
down_revision: Union[str, Sequence[str], None] = '683f77be6a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable the pgvector extension in PostgreSQL."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Disable the pgvector extension in PostgreSQL."""
    op.execute("DROP EXTENSION IF EXISTS vector")
