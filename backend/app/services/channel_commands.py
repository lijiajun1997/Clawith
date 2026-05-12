"""Magic commands (/model, /stop, /skill) for IM channel messages.

Intercepted BEFORE messages reach the LLM so that control commands
never become conversation input.
"""

import asyncio
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from loguru import logger

_settings = get_settings()
_AGENT_DATA = Path(_settings.AGENT_DATA_DIR)


# ── Task registry for /stop cancellation ──────────────────────

_running_llm_tasks: dict[str, asyncio.Task] = {}


def register_running_task(conv_id: str, task: asyncio.Task) -> None:
    _running_llm_tasks[conv_id] = task


def unregister_running_task(conv_id: str) -> None:
    _running_llm_tasks.pop(conv_id, None)


def cancel_running_task(conv_id: str) -> bool:
    task = _running_llm_tasks.get(conv_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


# ── Skill workspace helpers ───────────────────────────────────


def _parse_skill_frontmatter(content: str, filename: str) -> tuple[str, str]:
    """Parse YAML frontmatter from a skill .md file. Returns (name, description)."""
    name = filename.replace("_", " ").replace("-", " ")
    description = ""
    stripped = content.strip()
    if stripped.startswith("---"):
        end = stripped.find("---", 3)
        if end != -1:
            frontmatter = stripped[3:end].strip()
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line.lower().startswith("name:"):
                    val = line[5:].strip().strip('"').strip("'")
                    if val:
                        name = val
                elif line.lower().startswith("description:"):
                    val = line[12:].strip().strip('"').strip("'")
                    if val:
                        description = val[:200]
            if description:
                return name, description
    for line in stripped.split("\n"):
        line = line.strip()
        if line in ("---",) or line.startswith("name:") or line.startswith("description:"):
            continue
        if line and not line.startswith("#"):
            description = line[:200]
            break
    if not description:
        lines = stripped.split("\n")
        if lines:
            description = lines[0].strip().lstrip("# ")[:200]
    return name, description


def _load_agent_skills(agent_id: uuid.UUID) -> list[tuple[str, str]]:
    """Load skill (name, description) from agent's workspace skills/ directory."""
    skills_dir = _AGENT_DATA / str(agent_id) / "skills"
    if not skills_dir.exists():
        return []
    result: list[tuple[str, str]] = []
    for entry in sorted(skills_dir.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            skill_md = entry / "SKILL.md"
            if not skill_md.exists():
                skill_md = entry / "skill.md"
            if skill_md.exists():
                try:
                    content = skill_md.read_text(encoding="utf-8", errors="replace").strip()
                    name, desc = _parse_skill_frontmatter(content, entry.name)
                    result.append((name, desc))
                except Exception:
                    result.append((entry.name, ""))
        elif entry.suffix == ".md" and entry.is_file():
            try:
                content = entry.read_text(encoding="utf-8", errors="replace").strip()
                name, desc = _parse_skill_frontmatter(content, entry.stem)
                result.append((name, desc))
            except Exception:
                result.append((entry.stem, ""))
    return result


# ── Command detection ────────────────────────────────────────


async def detect_and_handle_command(
    db: AsyncSession,
    agent_id: uuid.UUID,
    user_text: str,
    conv_id: str,
    tenant_id: uuid.UUID | None = None,
    current_model_id: uuid.UUID | None = None,
) -> tuple[bool, str | None, str | None]:
    """Detect and handle magic commands in channel messages.

    Returns (handled, reply, rewritten_text):
    - (False, None, None): not a command, proceed normally
    - (True, reply, None): command handled, send reply to user (skip LLM)
    - (True, None, rewritten_text): command handled, use rewritten_text as user message (call LLM)

    tenant_id and current_model_id are optional hints to avoid redundant DB lookups
    when the caller already has the agent loaded.
    """
    text = user_text.strip()
    if not text.startswith("/"):
        return False, None, None

    lowered = text.lower()

    # ── /stop (no DB needed) ──
    if re.match(r"^/stop\s*$", lowered):
        ok = cancel_running_task(conv_id)
        return (True, "已停止生成。", None) if ok else (True, "没有正在进行的生成。", None)

    # ── /model ──
    m_model = re.match(r"^/model\s*(\d*)\s*$", lowered)
    m_skill = re.match(r"^/skill\s*(\d*)\s*(.*)$", lowered)

    if m_model:
        from app.models.llm import LLMModel

        # Resolve tenant_id if not provided by caller
        tid = tenant_id
        cur_mid = current_model_id
        if tid is None:
            from app.models.agent import Agent as AgentModel
            agent_r = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
            agent = agent_r.scalar_one_or_none()
            if not agent:
                return True, "Agent not found.", None
            tid = agent.tenant_id
            cur_mid = agent.primary_model_id

        models_r = await db.execute(
            select(LLMModel)
            .where(LLMModel.enabled == True, LLMModel.tenant_id == tid)
            .order_by(LLMModel.created_at.asc())
        )
        models = models_r.scalars().all()
        if not models:
            return True, "此租户没有可用模型。", None

        num_str = m_model.group(1)
        if not num_str:
            lines = ["可用模型："]
            for i, mdl in enumerate(models, 1):
                label = mdl.label or mdl.model
                marker = "（当前）" if mdl.id == cur_mid else ""
                lines.append(f"{i}. {label} {marker}")
            lines.append("输入 /model 编号 切换模型")
            return True, "\n".join(lines), None

        n = int(num_str)
        if n < 1 or n > len(models):
            return True, f"无效编号，请输入 1-{len(models)}", None

        # Load agent for update (only when actually switching)
        from app.models.agent import Agent as AgentModel
        agent_r = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
        agent = agent_r.scalar_one_or_none()
        if not agent:
            return True, "Agent not found.", None
        agent.primary_model_id = models[n - 1].id
        await db.commit()
        label = models[n - 1].label or models[n - 1].model
        logger.info(f"[ChannelCmd] Agent {agent_id} model switched to {label}")
        return True, f"已切换到: {label}", None

    if m_skill:
        skills = _load_agent_skills(agent_id)
        if not skills:
            return True, "此 Agent 未部署技能。在管理后台将技能部署到此 Agent 后可使用 /skill 调用。", None

        num_str = m_skill.group(1)
        rest = m_skill.group(2).strip()

        if not num_str:
            lines = ["可用技能："]
            for i, (name, desc) in enumerate(skills, 1):
                lines.append(f"{i}. {name} — {desc[:60]}")
            lines.append("输入 /skill 编号 <你的问题> 使用技能")
            return True, "\n".join(lines), None

        n = int(num_str)
        if n < 1 or n > len(skills):
            return True, f"无效编号，请输入 1-{len(skills)}", None

        skill_name = skills[n - 1][0]
        if not rest:
            return True, f"技能: {skill_name}\n{skills[n - 1][1]}\n用法: /skill {n} <你的问题>", None

        rewritten = f"[{skill_name}] {rest}"
        logger.info(f"[ChannelCmd] Skill injected: {skill_name}")
        return True, None, rewritten

    # Unknown /-command → pass through to LLM
    return False, None, None
