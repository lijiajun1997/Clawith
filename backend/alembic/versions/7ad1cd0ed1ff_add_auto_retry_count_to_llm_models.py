"""add_auto_retry_count_to_llm_models

Revision ID: 7ad1cd0ed1ff
Revises: add_tool_source
Create Date: 2026-03-30 16:04:57.467845
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ad1cd0ed1ff'
down_revision: Union[str, None] = 'add_tool_source'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auto_retry_count column to llm_models table
    op.add_column('llm_models', sa.Column('auto_retry_count', sa.Integer(), nullable=True, server_default='3'))


def downgrade() -> None:
    # Remove auto_retry_count column from llm_models table
    op.drop_column('llm_models', 'auto_retry_count')
