"""add custom_title flag to chat_sessions

Revision ID: add_custom_title_flag
Revises:
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_custom_title_flag'
down_revision = '20260423_chat_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('custom_title', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'custom_title')
