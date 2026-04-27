"""set context_window_size default to 50

Revision ID: set_context_window_50
Revises: merge_heads_20260427
Create Date: 2026-04-27
"""
from alembic import op

revision = 'set_context_window_50'
down_revision = 'merge_heads_20260427'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE agents SET context_window_size = 50 WHERE context_window_size IS NULL OR context_window_size != 50")


def downgrade() -> None:
    pass
