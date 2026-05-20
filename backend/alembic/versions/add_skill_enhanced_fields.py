"""Add enhanced fields to skills table.

Revision ID: 20260515_skill_enhanced
Revises: 20260513_recent_files
Create Date: 2026-05-15
"""
import sqlalchemy as sa
from alembic import op

revision = "20260515_skill_enhanced"
down_revision = "20260513_recent_files"
branch_labels = None
depends_on = None

# emoji -> tabler icon 映射，迁移旧数据
EMOJI_TO_TABLER = {
    "📋": "IconClipboard",
    "📝": "IconPencil",
    "📄": "IconFileText",
    "🛠️": "IconTool",
    "🔍": "IconSearch",
    "🤖": "IconRobot",
    "--": "IconPackages",
    "": "IconPackages",
}


def upgrade() -> None:
    # 扩展 icon 字段长度，支持 tabler 图标名
    op.alter_column("skills", "icon",
                    existing_type=sa.String(10),
                    type_=sa.String(100),
                    existing_nullable=False)
    # 新增字段
    op.add_column("skills", sa.Column("icon_type", sa.String(20), server_default="tabler", nullable=False))
    op.add_column("skills", sa.Column("author", sa.String(200), nullable=True))
    op.add_column("skills", sa.Column("version", sa.String(20), server_default="1.0.0", nullable=False))
    op.add_column("skills", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    # 迁移旧分类名
    op.execute("UPDATE skills SET category = '其他' WHERE category IN ('general', 'custom')")
    # 迁移 emoji icon -> tabler icon name（使用 text + bindparam 避免编码问题）
    from sqlalchemy import text
    conn = op.get_bind()
    for emoji, tabler in EMOJI_TO_TABLER.items():
        if emoji:
            conn.execute(
                text("UPDATE skills SET icon = :tabler WHERE icon = :emoji"),
                {"tabler": tabler, "emoji": emoji}
            )
    # 将所有非 Icon 开头的 icon 设为默认
    conn.execute(text("UPDATE skills SET icon = 'IconPackages' WHERE icon NOT LIKE 'Icon%'"))


def downgrade() -> None:
    op.alter_column("skills", "icon",
                    existing_type=sa.String(100),
                    type_=sa.String(10),
                    existing_nullable=False)
    op.drop_column("skills", "updated_at")
    op.drop_column("skills", "version")
    op.drop_column("skills", "author")
    op.drop_column("skills", "icon_type")
