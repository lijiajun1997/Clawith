"""Add context_window_size to llm_models for token-level context management.

Revision ID: 20260512_llm_ctx_window
Revises: 20260507_activity_composite_idx
Create Date: 2026-05-12
"""
from alembic import op


revision = "20260512_llm_ctx_window"
down_revision = "add_tenant_default_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE llm_models ADD COLUMN IF NOT EXISTS context_window_size INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE llm_models DROP COLUMN IF EXISTS context_window_size")
