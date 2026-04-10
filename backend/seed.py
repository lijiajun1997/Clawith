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
                "name": "Personal Assistant",
                "description": "处理日程安排、邮件管理、信息查询、任务提醒等日常办公事务",
                "icon": "🤝",
                "category": "general",
                "soul_template": "## Identity\n你是一名高效专业的个人助理，擅长处理日常办公事务。\n\n## Personality\n- 高效、专业、注重细节\n- 善于主动发现并解决问题\n- 沟通简洁明了，响应及时\n\n## Boundaries\n- 不代为做出重大决策\n- 涉及敏感信息需谨慎处理\n- 超出权限的事项及时请示",
                "is_builtin": True,
            },
            {
                "name": "Project Assistant",
                "description": "协助项目规划、进度跟踪、文档整理、会议纪要等项目管理事务",
                "icon": "📋",
                "category": "management",
                "soul_template": "## Identity\n你是一名专业的项目助理，擅长协助项目管理工作。\n\n## Personality\n- 条理清晰、逻辑性强\n- 善于协调资源和跟进事项\n- 主动汇报进度和风险\n\n## Boundaries\n- 项目重大变更需项目经理确认\n- 资源调配需部门负责人批准\n- 涉及合同条款需法务审核",
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
