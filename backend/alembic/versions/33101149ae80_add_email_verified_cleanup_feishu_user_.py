"""add email_verified cleanup feishu_user_id

Revision ID: 33101149ae80
Revises: add_sso_login_enabled
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33101149ae80'
down_revision: Union[str, None] = 'add_sso_login_enabled'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add email_verified column with default True for backward compatibility
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT TRUE
    """)

    # Set existing users to verified
    op.execute("""
        UPDATE users SET email_verified = TRUE WHERE email_verified IS NULL
    """)

    # 2. Drop deprecated feishu_user_id column (no longer needed with OrgMember-based identity)
    op.execute("""
        ALTER TABLE users DROP COLUMN IF EXISTS feishu_user_id
    """)


def downgrade() -> None:
    op.add_column('users', sa.Column('feishu_user_id', sa.String(255), nullable=True))
    op.drop_column('users', 'email_verified')
