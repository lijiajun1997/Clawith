"""Add recent_files table for file operation tracking.

Revision ID: 20260513_recent_files
Revises: 20260513_skill_call_enum
Create Date: 2026-05-13
"""
import sqlalchemy as sa
from alembic import op

revision = "20260513_recent_files"
down_revision = "20260513_skill_call_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recent_files",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="agent"),
        sa.Column("actor_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("file_size", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recent_files_agent_created", "recent_files", ["agent_id", "created_at"])
    op.create_index("ix_recent_files_agent_path", "recent_files", ["agent_id", "path"])


def downgrade() -> None:
    op.drop_index("ix_recent_files_agent_path", table_name="recent_files")
    op.drop_index("ix_recent_files_agent_created", table_name="recent_files")
    op.drop_table("recent_files")
