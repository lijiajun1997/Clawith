"""Recent file tracking service.

Provides fire-and-forget tracking of file mutations and an indexed DB
query that replaces filesystem scanning for the "Recent Files" sidebar.

Design principles:
  - Zero impact on callers: fire-and-forget via asyncio.create_task.
  - Own DB session: never shares the caller's session / connection.
  - No filesystem I/O: file_size is inferred from content length, not stat().
  - Graceful degradation: every exception is silently swallowed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import delete, func, select, text, update

from app.database import async_session
from app.models.recent_file import RecentFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal counter for probabilistic pruning
# ---------------------------------------------------------------------------
_prune_counter = 0
_PRUNE_INTERVAL = 20  # prune once every N track_file calls
_MAX_ENTRIES_PER_AGENT = 100


# ---------------------------------------------------------------------------
# Core tracking
# ---------------------------------------------------------------------------

async def track_file(
    *,
    agent_id: Any,
    path: str,
    operation: str,
    actor_type: str = "agent",
    actor_id: Any | None = None,
    file_size: int = 0,
) -> None:
    """Record a file operation.  Uses its own DB session — safe to call
    from fire-and-forget contexts."""
    try:
        normalized = path.replace("\\", "/").strip("/")
        if not normalized:
            return
        filename = normalized.rsplit("/", 1)[-1]

        async with async_session() as db:
            # Upsert: if same agent+path was recorded within 60 s, update it
            now_val = await db.execute(select(func.now()))
            now_ts = now_val.scalar()
            cutoff_q = await db.execute(
                select(func.now() - text("INTERVAL '60 SECONDS'"))
            )
            cutoff = cutoff_q.scalar()

            existing = await db.execute(
                select(RecentFile)
                .where(
                    RecentFile.agent_id == agent_id,
                    RecentFile.path == normalized,
                    RecentFile.created_at >= cutoff,
                )
                .order_by(RecentFile.created_at.desc())
                .limit(1)
            )
            row = existing.scalar_one_or_none()
            if row:
                row.operation = operation
                row.file_size = file_size
                row.actor_type = actor_type
                row.actor_id = actor_id
                row.created_at = now_ts
            else:
                db.add(
                    RecentFile(
                        agent_id=agent_id,
                        path=normalized,
                        filename=filename,
                        operation=operation,
                        actor_type=actor_type,
                        actor_id=actor_id,
                        file_size=file_size,
                        created_at=now_ts,
                    )
                )
            await db.commit()

            # Probabilistic prune
            global _prune_counter
            _prune_counter += 1
            if _prune_counter % _PRUNE_INTERVAL == 0:
                await _prune_old_entries(db, agent_id)

    except Exception:
        logger.debug("track_file failed silently", exc_info=True)


def track_file_fire_and_forget(
    *,
    agent_id: Any,
    path: str,
    operation: str,
    **kwargs,
) -> None:
    """Non-blocking wrapper.  Schedules *track_file* as a background task
    so the caller is never delayed."""
    try:
        asyncio.get_running_loop().create_task(
            track_file(agent_id=agent_id, path=path, operation=operation, **kwargs)
        )
    except Exception:
        logger.debug("track_file_fire_and_forget failed silently", exc_info=True)


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

async def _prune_old_entries(db, agent_id: Any) -> None:
    """Keep only the latest *_MAX_ENTRIES_PER_AGENT* rows for an agent."""
    try:
        sub = (
            select(RecentFile.id)
            .where(RecentFile.agent_id == agent_id)
            .order_by(RecentFile.created_at.desc())
            .limit(_MAX_ENTRIES_PER_AGENT)
        )
        await db.execute(
            delete(RecentFile).where(
                RecentFile.agent_id == agent_id,
                RecentFile.id.not_in(sub),
            )
        )
        await db.commit()
    except Exception:
        logger.debug("_prune_old_entries failed", exc_info=True)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

_CODE_EXTS = (
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h",
    ".jsx", ".tsx", ".sh", ".bat", ".ps1", ".rb", ".php", ".css",
    ".scss", ".less", ".vue", ".svelte", ".kt", ".swift", ".m",
)


async def get_recent_files(
    db,
    *,
    agent_id: Any,
    limit: int = 30,
    offset: int = 0,
    exclude_code: bool = False,
) -> tuple[list[dict], int]:
    """Return (file_list, total_count) for the recent-files sidebar."""
    base_q = (
        select(RecentFile)
        .where(RecentFile.agent_id == agent_id, RecentFile.operation != "delete")
        .order_by(RecentFile.created_at.desc())
    )
    if exclude_code:
        for ext in _CODE_EXTS:
            base_q = base_q.where(~RecentFile.path.endswith(ext))

    # Total count
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated rows
    rows = (await db.execute(base_q.offset(offset).limit(limit))).scalars().all()

    files = []
    for r in rows:
        files.append({
            "name": r.filename,
            "path": r.path,
            "is_dir": False,
            "size": r.file_size,
            "modified_at": r.created_at.isoformat() if r.created_at else "",
            "operation": r.operation,
            "url": f"/api/agents/{agent_id}/files/download?path={r.path}",
        })
    return files, total
