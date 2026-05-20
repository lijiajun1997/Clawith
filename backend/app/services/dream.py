"""Dream service — daily review and reflection for agents.

Runs at midnight in each agent's timezone. Agents review their day's
conversations, update memory, analyze tool/skill usage, and optionally
send optimization suggestions to a collector agent.

Runs as a background task inside the FastAPI process.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from loguru import logger
from sqlalchemy import select, update

from app.config import get_settings

settings = get_settings()
PERSISTENT_DATA = Path(settings.AGENT_DATA_DIR)

DEFAULT_DREAM_INSTRUCTION = """[Dream Mode — 每日复盘]

这是你的每日复盘时间。请按以下步骤完成今日复盘。

## Phase 1: 阅读对话记录

1. 使用 `list_files` 查看 conversations 目录下的文件列表
2. 阅读今日所有对话记录文件（文件名包含今日日期的 JSON 文件）
3. 重点关注：用户提出的问题、你的回复质量、工具调用情况

## Phase 2: 整理和复盘

1. 总结今日工作要点和关键发现
2. 记录学到的经验教训
3. 识别可以改进的回复或处理方式

## Phase 3: 更新记忆

1. 将有价值的经验写入 memory/memory.md
2. 保持记忆简洁有序，删除过时内容，补充新经验
3. 不要重复记录已有内容

## Phase 4: 分析工具和技能调用

1. 回顾今日所有 tool_call 记录
2. 识别反复调用失败的工具或走弯路的情况
3. 如果发现对 skill 有优化建议：
   - 整理失败记录和改进建议
   - 使用 `send_message_to_agent` 发送给 AI收集助手

## Phase 5: 总结

- 如果一切正常，无需特别关注，回复 DREAM_OK
- 否则简要总结你的复盘结果

⚠️ 关键原则：
- 复盘要基于实际对话内容，不要编造
- 记忆更新要精炼，避免冗余
- 只有真正有价值的优化建议才发送给收集助手
"""


def _count_conversations_for_date(agent_id: uuid.UUID, target_date: str, tz_name: str) -> int:
    """Count conversation entries for a specific local date.

    Scans all conversation JSON files and counts entries whose timestamp
    falls on target_date in the agent's timezone.
    """
    conv_dir = PERSISTENT_DATA / str(agent_id) / "conversations"
    if not conv_dir.exists():
        return 0

    try:
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo("UTC")
    except ImportError:
        tz = timezone.utc

    total = 0
    for f in conv_dir.glob("*.json"):
        try:
            entries = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                continue
            for entry in entries:
                ts = entry.get("timestamp", "")
                if not ts:
                    continue
                try:
                    entry_dt = datetime.fromisoformat(ts)
                    if entry_dt.tzinfo is None:
                        entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                    entry_local = entry_dt.astimezone(tz)
                    if entry_local.strftime("%Y-%m-%d") == target_date:
                        total += 1
                except (ValueError, TypeError):
                    continue
        except (json.JSONDecodeError, OSError):
            continue

    return total


def _is_midnight_window(tz_name: str, window_minutes: int = 30) -> bool:
    """Check if current time is within a midnight window in the given timezone.

    Default window: ±30 minutes around midnight (23:30~00:30).
    """
    try:
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz)
        current_minutes = now_local.hour * 60 + now_local.minute
        # Window: [1440 - window_minutes, 1440) ∪ [0, window_minutes)
        return current_minutes >= (1440 - window_minutes) or current_minutes < window_minutes
    except Exception:
        return False


def _today_midnight_utc(tz_name: str) -> datetime:
    """Get today's midnight in agent's timezone, converted to UTC."""
    try:
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz)
        midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        # If we're past midnight but before 00:30, "today's midnight" already passed
        # We want the midnight that just happened
        return midnight_local.astimezone(timezone.utc)
    except Exception:
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _yesterday_local_date(tz_name: str) -> str:
    """Get yesterday's date string in the agent's timezone."""
    try:
        from zoneinfo import ZoneInfo
        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo("UTC")
        now_local = datetime.now(tz)
        yesterday = now_local - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
    except Exception:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")


async def _get_dream_config(tenant_id: uuid.UUID) -> dict:
    """Get dream configuration from TenantSetting."""
    from app.database import async_session
    from app.models.tenant_setting import TenantSetting

    config = {"min_conversations": 20}
    try:
        async with async_session() as db:
            result = await db.execute(
                select(TenantSetting).where(
                    TenantSetting.tenant_id == tenant_id,
                    TenantSetting.key == "company_dream_config",
                )
            )
            record = result.scalar_one_or_none()
            if record and record.value:
                config.update(record.value)
    except Exception as e:
        logger.warning(f"[Dream] Failed to load dream config for tenant {tenant_id}: {e}")
    return config


async def _execute_dream(agent_id: uuid.UUID):
    """Execute a single dream session for an agent.

    Three-phase DB pattern (same as heartbeat):
      Phase 1: Read agent, model, context → commit
      Phase 2: LLM tool loop (no DB connection held)
      Phase 3: Write token usage + last_dream_at → commit
    """
    from app.services.heartbeat import _agent_task_semaphore
    async with _agent_task_semaphore:
        await _execute_dream_inner(agent_id)


async def _execute_dream_inner(agent_id: uuid.UUID):
    """Inner dream logic (called under semaphore)."""
    try:
        from app.database import async_session
        from app.models.agent import Agent
        from app.models.llm import LLMModel

        # ── Phase 1: Read context ──
        agent_name = ""
        agent_role = ""
        agent_creator_id = None
        model_provider = ""
        model_api_key = ""
        model_model = ""
        model_base_url = None
        model_temperature = None
        model_max_output_tokens = None
        model_request_timeout = None
        dream_instruction = DEFAULT_DREAM_INSTRUCTION

        async with async_session() as db:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                return

            model_id = agent.primary_model_id or agent.fallback_model_id
            if not model_id:
                return

            model_result = await db.execute(select(LLMModel).where(LLMModel.id == model_id))
            model = model_result.scalar_one_or_none()
            if not model:
                return

            agent_name = agent.name
            agent_role = agent.role_description or ""
            agent_creator_id = agent.creator_id
            model_provider = model.provider
            from app.services.llm_utils import get_model_api_key
            model_api_key = get_model_api_key(model)
            model_model = model.model
            model_base_url = model.base_url
            model_temperature = model.temperature
            model_max_output_tokens = getattr(model, 'max_output_tokens', None)
            model_request_timeout = getattr(model, 'request_timeout', None)

            # Read DREAM.md if exists
            ws_root = PERSISTENT_DATA / str(agent_id)
            dream_file = ws_root / "DREAM.md"
            if dream_file.exists():
                try:
                    custom = dream_file.read_text(encoding="utf-8", errors="replace").strip()
                    if custom:
                        dream_instruction = custom
                except Exception:
                    pass

            # Build agent context
            from app.services.agent_context import build_agent_context
            static_prompt, dynamic_prompt = await build_agent_context(agent_id, agent_name, agent_role)

            # Fetch recent activity for dream context (100 entries)
            recent_context = ""
            try:
                from app.models.activity_log import AgentActivityLog
                recent_result = await db.execute(
                    select(AgentActivityLog)
                    .where(AgentActivityLog.agent_id == agent_id)
                    .order_by(AgentActivityLog.created_at.desc())
                    .limit(100)
                )
                recent_activities = recent_result.scalars().all()
                if recent_activities:
                    itms = []
                    for act in reversed(recent_activities):
                        ts = act.created_at.strftime("%m-%d %H:%M") if act.created_at else ""
                        itms.append(f"- [{ts}] {act.action_type}: {act.summary[:120]}")
                    recent_context = "\n\n---\n## Recent Activity (last 100)\n" + "\n".join(itms)
            except Exception as e:
                logger.warning(f"[Dream] Failed to fetch recent activity: {e}")

            await db.commit()

        # ── Phase 2: LLM calls ──
        full_instruction = dream_instruction + recent_context

        from app.services.llm_utils import create_llm_client, get_max_tokens, LLMMessage, LLMError

        try:
            client = create_llm_client(
                provider=model_provider,
                api_key=model_api_key,
                model=model_model,
                base_url=model_base_url,
                timeout=float(model_request_timeout or 180.0),
            )
        except Exception as e:
            logger.error(f"[Dream] Failed to create LLM client: {e}")
            return

        from app.services.agent_tools import execute_tool, get_agent_tools_for_llm
        tools_for_llm = await get_agent_tools_for_llm(agent_id)

        from app.services.token_tracker import record_token_usage, extract_usage_tokens, estimate_tokens_from_chars

        llm_messages = [
            LLMMessage(role="system", content=static_prompt, dynamic_content=dynamic_prompt),
            LLMMessage(role="user", content=full_instruction),
        ]

        reply = ""
        _dream_tokens = 0

        for round_i in range(50):  # Full tool loop — dream needs to read files and analyze
            try:
                response = await client.complete(
                    messages=llm_messages,
                    tools=tools_for_llm,
                    temperature=model_temperature,
                    max_tokens=get_max_tokens(model_provider, model_model, model_max_output_tokens),
                )
            except LLMError as e:
                logger.error(f"[Dream] LLM error: {e}")
                reply = ""
                break
            except Exception as e:
                logger.error(f"[Dream] LLM call error: {e}")
                reply = ""
                break

            # Track tokens
            real_tokens = extract_usage_tokens(response.usage)
            if real_tokens:
                _dream_tokens += real_tokens
            else:
                round_chars = sum(len(m.content or '') for m in llm_messages) + len(response.content or '')
                _dream_tokens += estimate_tokens_from_chars(round_chars)

            if response.tool_calls:
                llm_messages.append(LLMMessage(
                    role="assistant",
                    content=response.content or None,
                    tool_calls=[{
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"],
                    } for tc in response.tool_calls],
                    reasoning_content=response.reasoning_content,
                ))

                _TOOLS_REQUIRING_ARGS = {
                    "write_file", "read_file", "delete_file", "read_document",
                    "send_message_to_agent", "send_feishu_message", "send_email",
                    "web_search", "jina_search", "jina_read",
                }
                _output_truncated = response.finish_reason == "length"

                for tc in response.tool_calls:
                    fn = tc["function"]
                    tool_name = fn["name"]
                    raw_args = fn.get("arguments", "{}")
                    logger.info(f"[Dream] {tool_name} args (len={len(raw_args or '')}): {repr((raw_args or '')[:200])}")
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        logger.warning(f"[Dream] JSON parse failed for {tool_name}")
                        args = {}

                    if _output_truncated:
                        llm_messages.append(LLMMessage(
                            role="tool",
                            tool_call_id=tc["id"],
                            content="Error: Response was truncated. Tool call NOT executed. Please retry with concise content.",
                        ))
                        continue

                    if not args and tool_name in _TOOLS_REQUIRING_ARGS:
                        llm_messages.append(LLMMessage(
                            role="tool",
                            tool_call_id=tc["id"],
                            content=f"Error: {tool_name} requires arguments. Please retry with correct parameters.",
                        ))
                        continue

                    tool_result = await execute_tool(tool_name, args, agent_id, agent_creator_id)
                    llm_messages.append(LLMMessage(
                        role="tool",
                        tool_call_id=tc["id"],
                        content=str(tool_result),
                    ))
            else:
                reply = response.content or ""
                break

        await client.close()

        # ── Phase 3: Write results ──
        async with async_session() as db:
            if _dream_tokens > 0:
                await record_token_usage(agent_id, _dream_tokens)

            await db.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(last_dream_at=datetime.now(timezone.utc))
            )
            await db.commit()

        # Log activity
        is_ok = "DREAM_OK" in reply.upper() if reply else False
        if not is_ok and reply:
            from app.services.activity_logger import log_activity
            await log_activity(
                agent_id, "dream",
                f"Dream 复盘: {reply[:80]}",
                detail={"reply": reply[:500]},
            )

        logger.info(f"🌙 Dream for {agent_name}: {'OK' if is_ok else reply[:60]}")

    except Exception as e:
        logger.exception(f"[Dream] Error for agent {agent_id}: {e}")


async def _dream_tick():
    """One dream tick: find agents eligible for dream."""
    from app.database import async_session
    from app.models.agent import Agent
    from app.services.audit_logger import write_audit_log
    from app.services.timezone_utils import get_agent_timezone_sync
    from app.models.tenant import Tenant

    now = datetime.now(timezone.utc)

    try:
        async with async_session() as db:
            result = await db.execute(
                select(Agent).where(
                    Agent.dream_enabled == True,
                    Agent.status.in_(["running", "idle"]),
                )
            )
            agents = result.scalars().all()

            # Pre-load tenants
            tenant_ids = {a.tenant_id for a in agents if a.tenant_id}
            tenants_by_id = {}
            if tenant_ids:
                t_result = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
                tenants_by_id = {t.id: t for t in t_result.scalars().all()}

            triggered = 0
            for agent in agents:
                if agent.is_expired:
                    continue
                if agent.expires_at and now >= agent.expires_at:
                    continue

                # Resolve timezone
                tenant = tenants_by_id.get(agent.tenant_id)
                tz_name = get_agent_timezone_sync(agent, tenant)

                # Check midnight window
                if not _is_midnight_window(tz_name):
                    continue

                # Check if already ran today
                midnight_utc = _today_midnight_utc(tz_name)
                if agent.last_dream_at and agent.last_dream_at >= midnight_utc:
                    continue

                # Count yesterday's conversations
                yesterday = _yesterday_local_date(tz_name)
                conv_count = _count_conversations_for_date(agent.id, yesterday, tz_name)

                # Get tenant dream config
                dream_config = await _get_dream_config(agent.tenant_id)
                min_conversations = dream_config.get("min_conversations", 20)

                if conv_count < min_conversations:
                    continue

                # Fire dream
                logger.info(f"🌙 Triggering dream for {agent.name} (conversations={conv_count})")
                await write_audit_log("dream_fire", {
                    "agent_name": agent.name,
                    "conv_count": conv_count,
                    "target_date": yesterday,
                }, agent_id=agent.id)
                asyncio.create_task(_execute_dream(agent.id))
                triggered += 1

            if triggered:
                await write_audit_log("dream_tick", {"eligible_agents": len(agents), "triggered": triggered})

    except Exception as e:
        logger.exception(f"[Dream] Tick error: {e}")
        await write_audit_log("dream_error", {"error": str(e)[:300]})


async def start_dream():
    """Start the background dream loop. Call from FastAPI startup."""
    logger.info("🌙 Agent dream service started (60s tick)")
    while True:
        await _dream_tick()
        await asyncio.sleep(60)
