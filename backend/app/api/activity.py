"""Activity log API — view agent work history."""

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.permissions import check_agent_access
from app.core.events import get_redis
from app.database import get_db
from app.models.activity_log import AgentActivityLog
from app.models.agent import Agent, AgentPermission
from app.models.user import User

router = APIRouter(tags=["activity"])


# ─── Dashboard aggregated endpoint ──────────────────────────

_VALID_CHANNELS = {"feishu", "web", "dingtalk", "wecom", "wechat"}
_CACHE_TTL = 30  # seconds


async def _build_dashboard_summary(tenant_id: uuid.UUID, db: AsyncSession, days: int = 90) -> dict:
    """Build dashboard summary from DB queries. Tenant-scoped, no per-user filtering."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    params = {"tid": tenant_id, "since": since}

    async def _q(sql: str) -> list:
        return (await db.execute(text(sql), params)).all()

    async def _q_safe(sql: str) -> list:
        """Execute query with rollback on failure to prevent cascading abort."""
        try:
            return (await db.execute(text(sql), params)).all()
        except Exception:
            await db.rollback()
            return []

    # Execute queries sequentially (asyncpg does not support concurrent queries on one session)
    rows_type_counts = await _q("""  -- Q1: activity type counts
            SELECT action_type, COUNT(*) AS count
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.created_at >= :since
            GROUP BY action_type ORDER BY count DESC
        """)
    rows_hourly = await _q("""  -- Q2: hourly trend (24h)
            SELECT DATE_TRUNC('hour', al.created_at) AS hour, COUNT(*) AS count
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY hour ORDER BY hour
        """)
    rows_conv = await _q("""  -- Q3: conversation channel daily
            SELECT DATE(al.created_at) AS day,
                   COALESCE(al.detail_json->>'channel', 'other') AS channel,
                   COUNT(*) AS count
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.action_type = 'chat_reply'
              AND al.created_at >= :since
            GROUP BY day, channel ORDER BY day
        """)
    rows_rank = await _q("""  -- Q4: agent activity rank
            SELECT a.id AS agent_id, a.name AS agent_name,
                   COUNT(al.id) FILTER (WHERE al.created_at >= NOW() - INTERVAL '1 day') AS count_day,
                   COUNT(al.id) FILTER (WHERE al.created_at >= NOW() - INTERVAL '7 days') AS count_week,
                   COUNT(al.id) FILTER (WHERE al.created_at >= NOW() - INTERVAL '30 days') AS count_month
            FROM agents a
            LEFT JOIN agent_activity_logs al ON al.agent_id = a.id AND al.created_at >= :since
            WHERE a.tenant_id = :tid
            GROUP BY a.id, a.name
            HAVING COUNT(al.id) > 0
            ORDER BY count_week DESC
        """)
    rows_tool = await _q_safe("""  -- Q5: tool call stats
            SELECT COALESCE(al.detail_json->>'tool', 'unknown') AS tool,
                   COUNT(*) AS calls,
                   COUNT(*) FILTER (WHERE al.detail_json->>'result' IS NULL
                                    OR LEFT(al.detail_json->>'result', 1) NOT IN (chr(10060), chr(9940))) AS success
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.action_type = 'tool_call' AND al.created_at >= :since
            GROUP BY tool ORDER BY calls DESC LIMIT 10
        """)
    rows_error = await _q("""  -- Q6: error trend (14d)
            SELECT DATE(al.created_at) AS day, COUNT(*) AS errors
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.action_type = 'error'
              AND al.created_at >= NOW() - INTERVAL '14 days'
            GROUP BY day ORDER BY day
        """)
    rows_recent = await _q_safe("""  -- Q7: recent activities
            SELECT al.id, al.agent_id, al.action_type, al.summary, al.created_at
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid
            ORDER BY al.created_at DESC LIMIT 50
        """)
    rows_daily = await _q_safe("""  -- Q8: daily stats
            SELECT DATE(al.created_at) AS day, al.action_type,
                   al.detail_json->>'tool' AS detail_tool, COUNT(*) AS count
            FROM agent_activity_logs al
            JOIN agents a ON a.id = al.agent_id
            WHERE a.tenant_id = :tid AND al.created_at >= :since
            GROUP BY day, al.action_type, al.detail_json->>'tool' ORDER BY day
        """)
    rows_task_agg = await _q_safe("""  -- Q9: task aggregation by status
            SELECT t.agent_id,
                   COUNT(*) FILTER (WHERE t.status = 'pending') AS pending,
                   COUNT(*) FILTER (WHERE t.status = 'doing') AS doing,
                   COUNT(*) FILTER (WHERE t.status = 'done') AS done,
                   COUNT(*) FILTER (WHERE t.status = 'done' AND t.completed_at >= CURRENT_DATE) AS completed_today
            FROM tasks t
            JOIN agents a ON a.id = t.agent_id
            WHERE a.tenant_id = :tid
            GROUP BY t.agent_id
        """)
    rows_task_top = await _q_safe("""  -- Q10: top 3 pending/doing tasks per agent
            SELECT agent_id, id, title, priority, status FROM (
                SELECT t.agent_id, t.id, t.title, t.priority, t.status,
                       ROW_NUMBER() OVER (
                           PARTITION BY t.agent_id ORDER BY
                               CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1
                                                WHEN 'medium' THEN 2 ELSE 3 END,
                               t.created_at DESC) AS rn
                FROM tasks t
                JOIN agents a ON a.id = t.agent_id
                WHERE a.tenant_id = :tid AND t.status IN ('pending', 'doing')
            ) sub WHERE rn <= 3
        """)

    # --- Build response ---
    activity_type_counts = [{"action_type": r.action_type, "count": r.count} for r in rows_type_counts]

    hourly_trend = [{"hour": r.hour.isoformat(), "count": r.count} for r in rows_hourly]

    conv_map: dict[str, dict] = {}
    for r in rows_conv:
        day = str(r.day)
        if day not in conv_map:
            conv_map[day] = {"date": day, "feishu": 0, "web": 0, "dingtalk": 0, "wecom": 0, "wechat": 0, "other": 0}
        ch = r.channel if r.channel in _VALID_CHANNELS else "other"
        conv_map[day][ch] += r.count
    conversation_channel_daily = list(conv_map.values())

    agent_activity_rank = [
        {"agent_id": str(r.agent_id), "agent_name": r.agent_name,
         "count_day": r.count_day, "count_week": r.count_week, "count_month": r.count_month}
        for r in rows_rank
    ]

    tool_call_stats = [{"tool": r.tool, "calls": r.calls, "success": r.success} for r in rows_tool]

    error_trend = [{"date": str(r.day), "errors": r.errors} for r in rows_error]

    recent_activities = [
        {"id": str(r.id), "agent_id": str(r.agent_id), "action_type": r.action_type,
         "summary": r.summary, "created_at": r.created_at.isoformat() if r.created_at else None}
        for r in rows_recent
    ]

    daily_stats = [
        {"date": str(r.day), "action_type": r.action_type,
         "detail_tool": r.detail_tool, "count": r.count}
        for r in rows_daily
    ]

    by_status = {"pending": 0, "doing": 0, "done": 0}
    completed_today = 0
    agent_task_agg: dict[str, dict] = {}
    for r in rows_task_agg:
        aid = str(r.agent_id)
        by_status["pending"] += r.pending
        by_status["doing"] += r.doing
        by_status["done"] += r.done
        completed_today += r.completed_today
        agent_task_agg[aid] = {
            "pending": r.pending, "doing": r.doing,
            "done": r.done,
            "completed_today": r.completed_today,
            "tasks": [],
        }
    for r in rows_task_top:
        aid = str(r.agent_id)
        if aid not in agent_task_agg:
            agent_task_agg[aid] = {"pending": 0, "doing": 0, "done": 0, "completed_today": 0, "tasks": []}
        agent_task_agg[aid]["tasks"].append({
            "id": str(r.id), "title": r.title,
            "priority": r.priority, "status": r.status,
        })
    task_summary = {
        "by_status": by_status,
        "completed_today": completed_today,
        "agent_tasks": [{"agent_id": aid, **data} for aid, data in agent_task_agg.items()],
    }

    return {
        "activity_type_counts": activity_type_counts,
        "hourly_trend": hourly_trend,
        "conversation_channel_daily": conversation_channel_daily,
        "agent_activity_rank": agent_activity_rank,
        "tool_call_stats": tool_call_stats,
        "error_trend": error_trend,
        "daily_stats": daily_stats,
        "recent_activities": recent_activities,
        "task_summary": task_summary,
    }


_EMPTY_SUMMARY = {
    "activity_type_counts": [], "hourly_trend": [], "conversation_channel_daily": [],
    "agent_activity_rank": [], "tool_call_stats": [], "error_trend": [],
    "daily_stats": [], "recent_activities": [],
    "task_summary": {"by_status": {"pending": 0, "doing": 0, "done": 0}, "completed_today": 0, "agent_tasks": []},
}


@router.get("/dashboard/activity-summary")
async def get_dashboard_activity_summary(
    days: int = Query(90, ge=1, le=90),
    tenant_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tenant-level aggregated dashboard data with Redis caching.

    Shows company-wide statistics — no per-user permission filtering.
    Cached for 30s per tenant to avoid repeated DB queries.
    """
    tid = uuid.UUID(tenant_id) if tenant_id else current_user.tenant_id
    if not tid:
        return _EMPTY_SUMMARY

    cache_key = f"dashboard_summary:{tid}:{days}"

    # Try Redis cache first
    try:
        r = await get_redis()
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        cached = None

    result = await _build_dashboard_summary(tid, db, days)

    # Cache the result
    try:
        r = await get_redis()
        await r.set(cache_key, json.dumps(result, default=str), ex=_CACHE_TTL)
    except Exception:
        pass

    return result


@router.get("/agents/{agent_id}/activity")
async def get_agent_activity(
    agent_id: uuid.UUID,
    limit: int = Query(50, le=2000),
    days: int = Query(0, ge=0, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent activity logs for an agent.

    When ``days`` > 0, only return records created within that many days.
    The limit cap is raised to 2000 to support dashboard charts.
    """
    await check_agent_access(db, current_user, agent_id)

    q = select(AgentActivityLog).where(AgentActivityLog.agent_id == agent_id)
    if days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.where(AgentActivityLog.created_at >= since)
    q = q.order_by(AgentActivityLog.created_at.desc()).limit(limit)

    result = await db.execute(q)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "action_type": log.action_type,
            "summary": log.summary,
            "detail": log.detail_json,
            "related_id": str(log.related_id) if log.related_id else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


@router.get("/agents/{agent_id}/activity/daily-stats")
async def get_agent_daily_stats(
    agent_id: uuid.UUID,
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return daily aggregated activity counts for dashboard charts.

    Returns: ``[ { "date": "2026-05-01", "action_type": "tool_call",
                     "detail_tool": "send_channel_file", "count": 5 }, ... ]``
    """
    await check_agent_access(db, current_user, agent_id)

    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Use raw SQL to avoid SQLAlchemy GROUP BY expression mismatch with JSON ->> cast
    rows = await db.execute(
        text("""
            SELECT DATE(created_at) AS day,
                   action_type,
                   detail_json->>'tool' AS detail_tool,
                   COUNT(*) AS count
            FROM agent_activity_logs
            WHERE agent_id = :aid AND created_at >= :since
            GROUP BY DATE(created_at), action_type, detail_json->>'tool'
            ORDER BY DATE(created_at)
        """),
        {"aid": str(agent_id), "since": since},
    )

    return [
        {
            "date": str(r.day),
            "action_type": r.action_type,
            "detail_tool": r.detail_tool,
            "count": r.count,
        }
        for r in rows.all()
    ]


# ─── Chat History (per-agent) ─────────────────────────────────

@router.get("/agents/{agent_id}/chat-history/conversations")
async def list_conversations(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all conversation partners for this agent (web users + other agents)."""
    await check_agent_access(db, current_user, agent_id)

    from app.models.audit import ChatMessage
    from app.models.agent import Agent
    from app.models.chat_session import ChatSession

    conversations = []

    # 1. Web chat conversations (from ChatMessage table, grouped by user)
    web_users_q = await db.execute(
        select(ChatMessage.user_id, func.max(ChatMessage.created_at).label("last_at"), func.count(ChatMessage.id).label("cnt"))
        .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id.like("web_%"))
        .group_by(ChatMessage.user_id)
    )
    for row in web_users_q.fetchall():
        user_id, last_at, cnt = row
        user_r = await db.execute(select(User.display_name).where(User.id == user_id))
        name = user_r.scalar_one_or_none() or "未知用户"
        # Get last message
        last_msg_r = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.agent_id == agent_id, ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc()).limit(1)
        )
        last_content = last_msg_r.scalar_one_or_none() or ""
        conversations.append({
            "conv_id": f"web_{user_id}",
            "partner_type": "user",
            "partner_id": str(user_id),
            "partner_name": f"👤 {name}",
            "last_message": last_content[:80],
            "message_count": cnt,
            "last_at": last_at.isoformat() if last_at else None,
        })

    # 1b. Feishu conversations (P2P and group)
    feishu_convs_q = await db.execute(
        select(
            ChatMessage.conversation_id,
            func.max(ChatMessage.created_at).label("last_at"),
            func.count(ChatMessage.id).label("cnt"),
        )
        .where(
            ChatMessage.agent_id == agent_id,
            ChatMessage.conversation_id.like("feishu_%"),
        )
        .group_by(ChatMessage.conversation_id)
    )
    for row in feishu_convs_q.fetchall():
        conv_id, last_at, cnt = row
        # Get last message
        last_msg_r = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id == conv_id)
            .order_by(ChatMessage.created_at.desc()).limit(1)
        )
        last_content = last_msg_r.scalar_one_or_none() or ""

        # Determine display name
        if conv_id.startswith("feishu_p2p_"):
            # Try to get sender name from first user message
            name_r = await db.execute(
                select(ChatMessage.content)
                .where(
                    ChatMessage.agent_id == agent_id,
                    ChatMessage.conversation_id == conv_id,
                    ChatMessage.role == "user",
                )
                .order_by(ChatMessage.created_at.asc()).limit(1)
            )
            first_msg = name_r.scalar_one_or_none() or ""
            # Extract sender name from [发送者: xxx] prefix
            import re
            sender_match = re.search(r'\[发送者:\s*([^\]]+?)(?:\s*\(ID:.*?\))?\]', first_msg)
            display_name = f"📱 {sender_match.group(1)}" if sender_match else f"📱 飞书用户"
        else:
            display_name = "👥 飞书群聊"

        conversations.append({
            "conv_id": conv_id,
            "partner_type": "feishu",
            "partner_id": conv_id,
            "partner_name": display_name,
            "last_message": last_content[:80],
            "message_count": cnt,
            "last_at": last_at.isoformat() if last_at else None,
        })

    # 1c. Slack conversations
    for prefix, icon, label in [("slack_", "💬", "Slack"), ("discord_", "🎮", "Discord")]:
        ch_convs_q = await db.execute(
            select(
                ChatMessage.conversation_id,
                func.max(ChatMessage.created_at).label("last_at"),
                func.count(ChatMessage.id).label("cnt"),
            )
            .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id.like(f"{prefix}%"))
            .group_by(ChatMessage.conversation_id)
        )
        for row in ch_convs_q.fetchall():
            conv_id, last_at, cnt = row
            last_msg_r = await db.execute(
                select(ChatMessage.content)
                .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id == conv_id)
                .order_by(ChatMessage.created_at.desc()).limit(1)
            )
            last_content = last_msg_r.scalar_one_or_none() or ""
            # Build a readable name from conv_id e.g. slack_C123_U456 → Slack C123
            parts = conv_id.split("_", 2)
            channel_part = parts[1] if len(parts) > 1 else conv_id
            display_name = f"{icon} {label} #{channel_part}" if channel_part != "dm" else f"{icon} {label} DM"
            conversations.append({
                "conv_id": conv_id,
                "partner_type": prefix.rstrip("_"),
                "partner_id": conv_id,
                "partner_name": display_name,
                "last_message": last_content[:80],
                "message_count": cnt,
                "last_at": last_at.isoformat() if last_at else None,
            })

    # 2. Agent-to-agent conversations (from ChatSession with peer_agent_id)
    agent_sessions_q = await db.execute(
        select(ChatSession).where(
            ChatSession.source_channel == "agent",
            (ChatSession.agent_id == agent_id) | (ChatSession.peer_agent_id == agent_id),
        )
    )
    for sess in agent_sessions_q.scalars().all():
        # Determine the partner agent
        partner_id = sess.peer_agent_id if sess.agent_id == agent_id else sess.agent_id
        agent_r = await db.execute(select(Agent.name).where(Agent.id == partner_id))
        partner_name = agent_r.scalar_one_or_none() or "未知数字员工"

        # Count messages in this session
        stats_q = await db.execute(
            select(func.count(ChatMessage.id), func.max(ChatMessage.created_at))
            .where(ChatMessage.conversation_id == str(sess.id))
        )
        stats = stats_q.fetchone()
        cnt = stats[0] if stats else 0
        last_at = stats[1] if stats else None

        # Get last message
        last_msg_r = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.conversation_id == str(sess.id))
            .order_by(ChatMessage.created_at.desc()).limit(1)
        )
        last_content = last_msg_r.scalar_one_or_none() or ""

        conversations.append({
            "conv_id": str(sess.id),
            "partner_type": "agent",
            "partner_id": str(partner_id),
            "partner_name": f"🤖 {partner_name}",
            "last_message": last_content[:80],
            "message_count": cnt,
            "last_at": last_at.isoformat() if last_at else None,
        })

    # Sort by last_at desc
    conversations.sort(key=lambda c: c["last_at"] or "", reverse=True)
    return conversations


@router.get("/agents/{agent_id}/chat-history/{conv_id:path}")
async def get_conversation_messages(
    agent_id: uuid.UUID,
    conv_id: str,
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a specific conversation."""
    await check_agent_access(db, current_user, agent_id)

    messages = []

    if conv_id.startswith("web_") or conv_id.startswith("feishu_") or conv_id.startswith("slack_") or conv_id.startswith("discord_"):
        from app.models.audit import ChatMessage
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.agent_id == agent_id, ChatMessage.conversation_id == conv_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        for m in result.scalars().all():
            content = m.content
            # Strip [发送者: xxx] prefix for display (identity shown in UI)
            if content.startswith("[发送者:"):
                import re
                content = re.sub(r'^\[发送者:[^\]]*\]\s*', '', content)
            messages.append({
                "id": str(m.id),
                "role": m.role,
                "content": content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })
    elif conv_id.startswith("agent_") or len(conv_id) == 36:
        # Agent-to-agent conversation — conv_id is the ChatSession UUID
        from app.models.audit import ChatMessage
        from app.models.agent import Agent
        from app.models.participant import Participant

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        name_cache = {}
        for m in result.scalars().all():
            # Determine sender name from participant_id
            sender_name = "未知"
            if m.participant_id:
                pid_str = str(m.participant_id)
                if pid_str not in name_cache:
                    p_r = await db.execute(select(Participant.display_name).where(Participant.id == m.participant_id))
                    name_cache[pid_str] = p_r.scalar_one_or_none() or "未知"
                sender_name = name_cache[pid_str]
            messages.append({
                "id": str(m.id),
                "role": m.role,
                "sender_name": sender_name,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

    return messages
