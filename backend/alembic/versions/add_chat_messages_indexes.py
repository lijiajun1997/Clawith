"""Add indexes for chat_messages table to optimize session listing performance.

This migration adds a critical index on conversation_id to fix the N+1 query
performance issue in the list_sessions API endpoint.

Revision ID: 20260423_add_chat_messages_indexes
Revises: 20260423_add_agent_permissions_indexes
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260423_chat_idx'
down_revision = '20260423_perm_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Critical index for: WHERE conversation_id = ?
    # This fixes the N+1 query performance issue in list_sessions API
    op.create_index(
        'ix_chat_messages_conversation_id',
        'chat_messages',
        ['conversation_id']
    )

    # Composite index for: WHERE agent_id = ? ORDER BY created_at DESC
    # This optimizes recent message queries for an agent
    op.create_index(
        'ix_chat_messages_agent_id_created_at',
        'chat_messages',
        ['agent_id', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_chat_messages_agent_id_created_at', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
