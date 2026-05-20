"""Add skill_call to activity_action_enum.

Revision ID: 20260513_skill_call_enum
Revises: 20260507_activity_composite_idx
Create Date: 2026-05-13
"""
from alembic import op


revision = '20260513_skill_call_enum'
down_revision = '20260507_activity_composite_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE activity_action_enum ADD VALUE IF NOT EXISTS 'skill_call'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
