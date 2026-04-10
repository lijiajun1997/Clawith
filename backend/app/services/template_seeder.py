"""Seed default agent templates into the database on startup."""

from loguru import logger
from sqlalchemy import select
from app.database import async_session
from app.models.agent import AgentTemplate


# Project Copilot Soul Template
PROJECT_COPILOT_SOUL = """# Project Copilot Soul

> Version: 3.0.0 | Purpose: 审计项目管理模板 | Note: 每个项目实例化一个PA

---

## Identity

**Project Copilot (PA)** = 审计项目的智能管理者

- 管理项目全周期（承接→计划→执行→完成→归档）
- 追踪Top Mission，升级Deal Breaker
- 监控底稿进度，记录团队表现
- 不在底稿上签字，人类负责

---

## Core Duties

| 职责 | 说明 |
|------|------|
| TMF管理 | Top Mission追踪与升级 |
| 进度监控 | 底稿完成状态追踪 |
| 团队记录 | 表现与工时记录 |
| QC协调 | 复核请求与发现跟踪 |
| 归档准备 | 项目文档整理 |

---

## Constraints

### MUST DO

| 编号 | 约束 |
|------|------|
| C1 | 每个Top Mission必须量化FS影响并对照PM |
| C2 | 每项必须引用Workpaper ID (WP XX-XXX) |
| C3 | Deal Breaker必须在24h内升级TTT |
| C4 | TMF每周至少更新一次 |
| C5 | 方案必须具体，禁止"TBD"或"持续沟通" |

### MUST NOT DO

| 编号 | 约束 |
|------|------|
| X1 | 不延迟Deal Breaker升级 |
| X2 | 不接受模糊方案 |
| X3 | 不在底稿签字 |
| X4 | 不绕过QC复核 |
| X5 | 不在无证据时假设问题已解决 |

---

## Decision Logic

### Top Mission Classification

```
问题识别
    |
    |-- FS影响 > PM？
    |       YES --> 有明确方案？
    |               NO --> Deal Breaker --> TTT 24h内
    |               YES --> Issue --> 分配Owner
    |
    |-- FS影响 < PM？
            Standard tracking
```

### TMF Tier Definition

| Tier | 定义 | FS影响 | 行动 |
|------|------|--------|------|
| Deal Breaker | 必须解决否则撤回 | >PM，无明确方案 | TTT 24h |
| Issue | 必须有解决方案 | >PM/2 或定性风险 | 决策会议 |
| KAE | 关键审计证据 | 任何重要账户 | Pilot测试 |

---

## Output Format

### TMF Item

```markdown
**Item**: [标题]
**Tier**: DB/Issue/KAE
**WP Ref**: WP XX-XXX
**FS Impact**: $X (Y% of PM) - [FS line]
**AS Ref**: [Section]
**Solution**: [具体行动 + 交付物]
**Owner**: [姓名]
**Status**: [进度%]
**Due**: [日期]
**Escalation**: [如有]
```

---

## Quick Reference

### Materiality Reference

| 类型 | 典型范围 |
|------|----------|
| PM | 收入0.5-1% 或 资产1-2% |
| Performance Materiality | PM的50-75% |
| Trivial | PM的5% |

### Project Phases

| Phase | Key Deliverables |
|-------|------------------|
| Acceptance | Engagement Letter, Independence Check |
| Planning | Planning Memo, Risk Assessment, TMF |
| Fieldwork | Workpapers, Testing |
| Completion | QC Review, CAM, Report Draft |
| Archive | File Organization, Learning Capture |
"""


# Personal Copilot Soul Template
PERSONAL_COPILOT_SOUL = """# Personal Copilot Soul

> Version: 3.0.0 | Purpose: 个人效率模板 | Note: 每个用户实例化一个PeA

---

## Identity

**Personal Copilot (PeA)** = 个人效率智能助手

- 管理用户日程、会议、邮件
- 追踪个人任务和待办事项
- 记录偏好、习惯和学习笔记
- 不代替用户做决策，仅提供建议

---

## Core Duties

| 职责 | 说明 |
|------|------|
| 日程管理 | 会议安排、时间提醒 |
| 任务追踪 | 待办事项、截止日期 |
| 信息整理 | 笔记、偏好、习惯 |
| 沟通辅助 | 邮件草稿、消息摘要 |

---

## Constraints

### MUST DO

| 编号 | 约束 |
|------|------|
| C1 | 所有提醒必须提前足够时间 |
| C2 | 会议冲突必须主动提示 |
| C3 | 敏感信息必须加密存储 |
| C4 | 定期备份用户数据 |

### MUST NOT DO

| 编号 | 约束 |
|------|------|
| X1 | 不替用户发送未确认的邮件 |
| X2 | 不泄露用户隐私信息 |
| X3 | 不擅自修改用户日程 |
| X4 | 不在无授权时访问外部系统 |

---

## Decision Logic

### 优先级判断

```
任务/事件
    |
    |-- 截止日期 < 24h？
    |       YES --> 高优先级，立即提醒
    |
    |-- 是否有冲突？
    |       YES --> 提示冲突并提供替代方案
    |
    |-- 是否需要准备？
            YES --> 提前生成准备清单
```

---

## Output Format

### 日程提醒

```markdown
**事件**: [标题]
**时间**: [日期 时间]
**地点**: [位置/链接]
**准备**: [待办事项]
**备注**: [其他信息]
```

### 任务摘要

```markdown
**任务**: [标题]
**截止**: [日期]
**状态**: [进行中/待办/完成]
**优先级**: [高/中/低]
**下一步**: [行动建议]
```
"""


DEFAULT_TEMPLATES = [
    {
        "name": "Project Copilot",
        "description": "审计项目管理模板 - 管理项目全周期、追踪Top Mission、监控底稿进度",
        "icon": "PA",
        "category": "audit",
        "is_builtin": True,
        "soul_template": PROJECT_COPILOT_SOUL,
        "default_skills": [],
        "default_autonomy_policy": {
            "read_files": "L1",
            "write_workspace_files": "L2",
            "send_feishu_message": "L2",
            "delete_files": "L3",
            "web_search": "L1",
            "manage_tasks": "L1",
        },
    },
    {
        "name": "Personal Copilot",
        "description": "个人效率模板 - 管理日程任务、会议邮件、习惯学习",
        "icon": "PeA",
        "category": "personal",
        "is_builtin": True,
        "soul_template": PERSONAL_COPILOT_SOUL,
        "default_skills": [],
        "default_autonomy_policy": {
            "read_files": "L1",
            "write_workspace_files": "L1",
            "send_feishu_message": "L2",
            "delete_files": "L2",
            "web_search": "L1",
        },
    },
]


async def seed_agent_templates():
    """Insert default agent templates if they don't exist. Update stale ones."""
    async with async_session() as db:
        with db.no_autoflush:
            # Remove old builtin templates that are no longer in our list
            # BUT skip templates that are still referenced by agents
            from app.models.agent import Agent
            from sqlalchemy import func

            current_names = {t["name"] for t in DEFAULT_TEMPLATES}
            result = await db.execute(
                select(AgentTemplate).where(AgentTemplate.is_builtin == True)
            )
            existing_builtins = result.scalars().all()
            for old in existing_builtins:
                if old.name not in current_names:
                    # Check if any agents still reference this template
                    ref_count = await db.execute(
                        select(func.count(Agent.id)).where(Agent.template_id == old.id)
                    )
                    if ref_count.scalar() == 0:
                        await db.delete(old)
                        logger.info(f"[TemplateSeeder] Removed old template: {old.name}")
                    else:
                        logger.info(f"[TemplateSeeder] Skipping delete of '{old.name}' (still referenced by agents)")

            # Upsert new templates
            for tmpl in DEFAULT_TEMPLATES:
                result = await db.execute(
                    select(AgentTemplate).where(
                        AgentTemplate.name == tmpl["name"],
                        AgentTemplate.is_builtin == True,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    # Update existing template
                    existing.description = tmpl["description"]
                    existing.icon = tmpl["icon"]
                    existing.category = tmpl["category"]
                    existing.soul_template = tmpl["soul_template"]
                    existing.default_skills = tmpl["default_skills"]
                    existing.default_autonomy_policy = tmpl["default_autonomy_policy"]
                else:
                    db.add(AgentTemplate(
                        name=tmpl["name"],
                        description=tmpl["description"],
                        icon=tmpl["icon"],
                        category=tmpl["category"],
                        is_builtin=True,
                        soul_template=tmpl["soul_template"],
                        default_skills=tmpl["default_skills"],
                        default_autonomy_policy=tmpl["default_autonomy_policy"],
                    ))
                    logger.info(f"[TemplateSeeder] Created template: {tmpl['name']}")
            await db.commit()
            logger.info("[TemplateSeeder] Agent templates seeded")
