"""Add memory system tables (token-based design).

Revision ID: add_memory_system
Revises: d9cbd43b62e5
Create Date: 2026-04-07

Tables:
- memory_system_configs: Company-level config
- agent_memory_configs: Agent-level overrides
- compression_summaries: Stored compression summaries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "add_memory_system"
down_revision = "d9cbd43b62e5"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Drop old tables if they exist (wrong schema from previous iteration)
    for tbl in ["memory_merge_logs", "memory_system_configs", "agent_memory_configs", "compression_summaries"]:
        if conn.dialect.has_table(conn, tbl):
            op.drop_table(tbl)

    # === Table: memory_system_configs ===
    op.create_table(
        "memory_system_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),

        sa.Column("context_window_tokens", sa.Integer, nullable=True),
        sa.Column("compress_threshold", sa.Float, server_default=sa.text("0.75")),
        sa.Column("preserve_ratio", sa.Float, server_default=sa.text("0.25")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),

        sa.UniqueConstraint("tenant_id", name="uq_memory_config_tenant"),
    )
    op.create_index("ix_memory_system_configs_tenant_id", "memory_system_configs", ["tenant_id"])

    # === Table: agent_memory_configs ===
    op.create_table(
        "agent_memory_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),

        sa.Column("context_window_tokens", sa.Integer, nullable=True),
        sa.Column("compress_threshold", sa.Float, nullable=True),
        sa.Column("preserve_ratio", sa.Float, nullable=True),

        sa.Column("last_compress_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_compressions", sa.Integer, server_default=sa.text("0")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_memory_configs_agent_id", "agent_memory_configs", ["agent_id"])
    op.create_unique_constraint("uq_agent_memory_configs_agent_id", "agent_memory_configs", ["agent_id"])

    # === Table: compression_summaries ===
    op.create_table(
        "compression_summaries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(100), nullable=True),

        sa.Column("summary_text", sa.String(10000), nullable=False),
        sa.Column("original_token_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("summary_token_count", sa.Integer, server_default=sa.text("0")),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_compression_summaries_agent_id", "compression_summaries", ["agent_id"])
    op.create_index("ix_compression_summaries_session_id", "compression_summaries", ["session_id"])


def downgrade():
    conn = op.get_bind()

    if conn.dialect.has_table(conn, "compression_summaries"):
        op.drop_table("compression_summaries")
    if conn.dialect.has_table(conn, "agent_memory_configs"):
        op.drop_table("agent_memory_configs")
    if conn.dialect.has_table(conn, "memory_system_configs"):
        op.drop_table("memory_system_configs")
