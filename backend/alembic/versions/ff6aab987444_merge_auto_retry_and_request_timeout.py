"""merge_auto_retry_and_request_timeout

Revision ID: ff6aab987444
Revises: 7ad1cd0ed1ff, d9cbd43b62e5
Create Date: 2026-04-02 01:13:29.203658
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff6aab987444'
down_revision: Union[str, None] = ('7ad1cd0ed1ff', 'd9cbd43b62e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
