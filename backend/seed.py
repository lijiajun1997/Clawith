"""Seed data script — creates built-in templates (run once for new deployments)."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.config import get_settings
from app.database import Base, engine, async_session
# Import ALL models so Base.metadata.create_all can resolve all FKs
from app.models.tenant import Tenant  # noqa: F401 — must be before user
from app.models.user import User  # noqa: F401
from app.models.agent import AgentTemplate  # noqa: F401
from app.models.llm import LLMModel  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.skill import Skill  # noqa: F401
from app.models.tool import Tool  # noqa: F401
from app.models.participant import Participant  # noqa: F401
from app.models.channel_config import ChannelConfig  # noqa: F401
from app.models.schedule import AgentSchedule  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.plaza import PlazaPost, PlazaComment  # noqa: F401
from app.models.activity_log import AgentActivityLog  # noqa: F401
from app.models.org import OrgDepartment, OrgMember, AgentRelationship, AgentAgentRelationship  # noqa: F401
from app.models.system_settings import SystemSetting  # noqa: F401
from app.models.invitation_code import InvitationCode  # noqa: F401


async def seed():
    """Create tables and seed initial data.

    Note: Default admin user is created in app/main.py on startup.
    This script only creates built-in agent templates.
    """
    settings = get_settings()

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created")

    async with async_session() as db:
        from sqlalchemy import select

        # 1. Default company (tenant)
        existing_tenant = await db.execute(select(Tenant).where(Tenant.slug == "default"))
        if not existing_tenant.scalar_one_or_none():
            db.add(Tenant(name="Default", slug="default", im_provider="web_only"))
            await db.commit()
            print("✅ Default company created")

        # 2. Built-in agent templates (for quick agent creation)
        templates = [
            {
                "name": "研究助手",
                "description": "专注于信息搜集、竞品分析、行业研究的数字员工",
                "icon": "🔬",
                "category": "research",
                "soul_template": "## Identity\n你是一名专业的研究助手，擅长信息搜集和分析。\n\n## Personality\n- 严谨细致\n- 数据驱动\n- 客观中立\n\n## Boundaries\n- 引用来源须标注\n- 不做主观判断",
                "is_builtin": True,
            },
            {
                "name": "项目管理助手",
                "description": "负责项目进度跟踪、任务分配、督办提醒的数字员工",
                "icon": "📋",
                "category": "management",
                "soul_template": "## Identity\n你是一名高效的项目管理助手。\n\n## Personality\n- 条理清晰\n- 主动跟进\n- 注重截止日期\n\n## Boundaries\n- 不擅自修改项目计划\n- 重大决策需确认",
                "is_builtin": True,
            },
            {
                "name": "客户服务助手",
                "description": "处理客户咨询、FAQ 回答、工单管理的数字员工",
                "icon": "💬",
                "category": "support",
                "soul_template": "## Identity\n你是一名热情专业的客户服务助手。\n\n## Personality\n- 友好热情\n- 耐心细致\n- 解决导向\n\n## Boundaries\n- 不承诺超出权限的内容\n- 敏感问题转人工",
                "is_builtin": True,
            },
            {
                "name": "数据分析师",
                "description": "数据查询、报表生成、趋势分析的数字员工",
                "icon": "📊",
                "category": "analytics",
                "soul_template": "## Identity\n你是一名数据分析专家。\n\n## Personality\n- 精确严谨\n- 善于可视化\n- 洞察力强\n\n## Boundaries\n- 数据安全第一\n- 不泄露原始数据",
                "is_builtin": True,
            },
            {
                "name": "内容创作助手",
                "description": "文案撰写、内容审核、社交媒体管理的数字员工",
                "icon": "✍️",
                "category": "content",
                "soul_template": "## Identity\n你是一名创意内容助手。\n\n## Personality\n- 创意丰富\n- 文字功底好\n- 了解营销\n\n## Boundaries\n- 遵守品牌调性\n- 发布前需审核",
                "is_builtin": True,
            },
        ]

        for tmpl in templates:
            existing = await db.execute(
                select(AgentTemplate).where(AgentTemplate.name == tmpl["name"])
            )
            if not existing.scalar_one_or_none():
                db.add(AgentTemplate(**tmpl))
                print(f"✅ Template created: {tmpl['icon']} {tmpl['name']}")

        await db.commit()

    print("\n🎉 Seed data complete!")


if __name__ == "__main__":
    asyncio.run(seed())
