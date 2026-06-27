"""'Remove RAG query tables'

Revision ID: 06e011c77292
Revises: 48add2a2bda8
Create Date: 2026-06-27 17:41:23.925522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06e011c77292'
down_revision: Union[str, Sequence[str], None] = '48add2a2bda8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('ix_rag_query_sources_rag_query_id'), table_name='rag_query_sources')
    op.drop_index(op.f('ix_rag_query_sources_document_id'), table_name='rag_query_sources')
    op.drop_index(op.f('ix_rag_query_sources_chunk_id'), table_name='rag_query_sources')
    op.drop_table('rag_query_sources')
    op.drop_index(op.f('ix_rag_queries_user_id'), table_name='rag_queries')
    op.drop_index(op.f('ix_rag_queries_session_id'), table_name='rag_queries')
    op.drop_table('rag_queries')
    sa.Enum(name='rag_query_status').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('rag_queries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('session_id', sa.Uuid(), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=True),
    sa.Column('provider', sa.String(length=255), nullable=True),
    sa.Column('model', sa.String(length=255), nullable=True),
    sa.Column('prompt_tokens', sa.Integer(), nullable=True),
    sa.Column('completion_tokens', sa.Integer(), nullable=True),
    sa.Column('total_tokens', sa.Integer(), nullable=True),
    sa.Column('top_k', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('queued', 'running', 'completed', 'failed', name='rag_query_status'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rag_queries_session_id'), 'rag_queries', ['session_id'], unique=False)
    op.create_index(op.f('ix_rag_queries_user_id'), 'rag_queries', ['user_id'], unique=False)
    op.create_table('rag_query_sources',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('rag_query_id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('chunk_id', sa.Uuid(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=False),
    sa.Column('content_preview', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['document_chunks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rag_query_id'], ['rag_queries.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rag_query_sources_chunk_id'), 'rag_query_sources', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_rag_query_sources_document_id'), 'rag_query_sources', ['document_id'], unique=False)
    op.create_index(op.f('ix_rag_query_sources_rag_query_id'), 'rag_query_sources', ['rag_query_id'], unique=False)
