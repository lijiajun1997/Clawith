"""Add Tenant.default_model_id + backfill per-tenant to earliest enabled model.

Revision ID: add_tenant_default_model
Revises: merge_heads_20260427
Create Date: 2026-05-06

Each tenant gets a default_model_id pointing at its first enabled LLM model
(by created_at ascending). Tenants with no enabled models stay NULL; the admin
picks one when they finally add a model (handled at the API layer).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'add_tenant_default_model'
down_revision: Union[str, None] = 'merge_heads_20260427'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE tenants
        ADD COLUMN IF NOT EXISTS default_model_id UUID
        REFERENCES llm_models(id) ON DELETE SET NULL
    """)

    op.execute("""
        UPDATE tenants t
        SET default_model_id = m.id
        FROM (
            SELECT DISTINCT ON (tenant_id) tenant_id, id
            FROM llm_models
            WHERE enabled = TRUE AND tenant_id IS NOT NULL
            ORDER BY tenant_id, created_at ASC
        ) m
        WHERE t.id = m.tenant_id AND t.default_model_id IS NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS default_model_id")
