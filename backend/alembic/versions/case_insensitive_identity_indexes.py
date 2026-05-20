"""Replace case-sensitive unique indexes on identities with case-insensitive ones.

Revision ID: 20260519_ci_identity_idx
Revises: 20260515_skill_enhanced
Create Date: 2026-05-19
"""
import sqlalchemy as sa
from alembic import op

revision = "20260519_ci_identity_idx"
down_revision = "20260515_skill_enhanced"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Email: case-insensitive unique index
    op.drop_index("ix_identities_email", table_name="identities")
    op.execute(
        "CREATE UNIQUE INDEX ix_identities_email ON identities (LOWER(email))"
    )

    # Username: case-insensitive unique index (NULL-safe partial index)
    op.drop_index("ix_identities_username", table_name="identities")
    op.execute(
        "CREATE UNIQUE INDEX ix_identities_username ON identities (LOWER(username)) "
        "WHERE username IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_identities_email", table_name="identities")
    op.execute(
        "CREATE UNIQUE INDEX ix_identities_email ON identities (email)"
    )

    op.drop_index("ix_identities_username", table_name="identities")
    op.execute(
        "CREATE UNIQUE INDEX ix_identities_username ON identities (username)"
    )
