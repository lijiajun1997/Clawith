"""merge heads 20260427

Revision ID: merge_heads_20260427
Revises: add_custom_title_flag, add_workspace_revisions
Create Date: 2026-04-27
"""
from alembic import op

revision = 'merge_heads_20260427'
down_revision = ('add_custom_title_flag', 'add_workspace_revisions')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
