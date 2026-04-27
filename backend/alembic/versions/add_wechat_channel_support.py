"""Add wechat and whatsapp to channel_type_enum.

Revision ID: add_wechat_channel
Revises: user_refactor_v1
Create Date: 2026-04-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_wechat_channel'
down_revision: Union[str, None] = 'user_refactor_v1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE channel_type_enum ADD VALUE IF NOT EXISTS 'wechat'")
    op.execute("ALTER TYPE channel_type_enum ADD VALUE IF NOT EXISTS 'whatsapp'")


def downgrade() -> None:
    pass
