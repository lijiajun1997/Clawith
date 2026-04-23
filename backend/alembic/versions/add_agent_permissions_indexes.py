"""Add indexes for agent_permissions table to optimize list_agents query.

This migration adds critical indexes on agent_permissions table to fix
the performance issue where loading the agent list page hangs/times out.

Revision ID: 20260423_add_agent_permissions_indexes
Revises: 20260423_add_notification_is_read_index
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260423_perm_idx'
down_revision = '20260423_notif_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Index for: WHERE agent_id = ?
    op.create_index(
        'ix_agent_permissions_agent_id',
        'agent_permissions',
        ['agent_id']
    )

    # Composite index for: WHERE scope_type = 'user' AND scope_id = ?
    # This is the critical index that fixes the agent list performance
    op.create_index(
        'ix_agent_permissions_scope_type_scope_id',
        'agent_permissions',
        ['scope_type', 'scope_id']
    )

    # Index for: WHERE scope_type = ?
    op.create_index(
        'ix_agent_permissions_scope_type',
        'agent_permissions',
        ['scope_type']
    )


def downgrade() -> None:
    op.drop_index('ix_agent_permissions_scope_type', table_name='agent_permissions')
    op.drop_index('ix_agent_permissions_scope_type_scope_id', table_name='agent_permissions')
    op.drop_index('ix_agent_permissions_agent_id', table_name='agent_permissions')
