"""Add dream_enabled and last_dream_at to agents table.

Revision ID: 20260520_add_dream_fields
Revises: 20260513_skill_call_enum
Create Date: 2026-05-20
"""
from alembic import op


revision = '20260520_add_dream_fields'
down_revision = '20260519_ci_identity_idx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS dream_enabled BOOLEAN DEFAULT TRUE,
        ADD COLUMN IF NOT EXISTS last_dream_at TIMESTAMP WITH TIME ZONE
    """)
    op.execute("ALTER TYPE activity_action_enum ADD VALUE IF NOT EXISTS 'dream'")


def downgrade() -> None:
    op.execute("""
        ALTER TABLE agents
        DROP COLUMN IF EXISTS dream_enabled,
        DROP COLUMN IF EXISTS last_dream_at
    """)
