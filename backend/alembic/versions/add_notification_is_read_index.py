"""Add composite index for notification unread queries.

This migration adds composite indexes on (user_id, is_read) and (agent_id, is_read)
to significantly improve the performance of the /api/notifications/unread-count endpoint.

Revision ID: 20260423_add_notification_is_read_index
Revises: 440261f5594f
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260423_notif_idx'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create composite index for user notifications (user_id, is_read)
    # This optimizes: SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = false
    op.create_index(
        'ix_notifications_user_id_is_read',
        'notifications',
        ['user_id', 'is_read']
    )

    # Create composite index for agent notifications (agent_id, is_read)
    # This optimizes: SELECT COUNT(*) FROM notifications WHERE agent_id = ? AND is_read = false
    op.create_index(
        'ix_notifications_agent_id_is_read',
        'notifications',
        ['agent_id', 'is_read']
    )


def downgrade() -> None:
    op.drop_index('ix_notifications_agent_id_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id_is_read', table_name='notifications')
