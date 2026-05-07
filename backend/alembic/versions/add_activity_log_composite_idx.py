"""Add composite index on agent_activity_logs for dashboard aggregation queries.

Supports the common query pattern: WHERE agent_id = ANY(...) AND created_at >= ...
followed by GROUP BY action_type.

Revision ID: 20260507_activity_composite_idx
Revises: (auto)
Create Date: 2026-05-07
"""
from alembic import op


revision = '20260507_activity_composite_idx'
down_revision = None  # Will be auto-resolved by Alembic
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        'ix_activity_logs_agent_created_type',
        'agent_activity_logs',
        ['agent_id', 'created_at', 'action_type'],
    )


def downgrade() -> None:
    op.drop_index('ix_activity_logs_agent_created_type', table_name='agent_activity_logs')
