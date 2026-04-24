"""Conversation logger — buffers chat events and flushes to workspace JSON files.

Files are stored at: {AGENT_DATA_DIR}/{agent_id}/conversations/{username}_{date}.json
The agent reads them via existing read_file / list_files tools.
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import get_settings
from app.services.agent_tools import WORKSPACE_ROOT

CONVERSATIONS_DIR = "conversations"
MAX_TOOL_RESULT_CHARS = 200
MAX_MESSAGE_CHARS = 2000
MAX_ARGS_CHARS = 300
FLUSH_INTERVAL_SECONDS = 60
FLUSH_THRESHOLD_MESSAGES = 10
MAX_BUFFER_SIZE = 500

_user_name_cache: dict[uuid.UUID, str] = {}


def _sanitize_filename(name: str) -> str:
    sanitized = re.sub(r"[^\w\-.]", "_", name.strip())
    return sanitized[:50] or "unknown"


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"...[truncated, {len(text)} total chars]"


async def resolve_user_name(user_id: uuid.UUID) -> str:
    if user_id in _user_name_cache:
        return _user_name_cache[user_id]
    try:
        from app.database import async_session
        from app.models.user import User
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                name = user.display_name or getattr(user, "username", None) or str(user_id)[:8]
                _user_name_cache[user_id] = name
                return name
    except Exception as e:
        logger.warning(f"[ConvLogger] User name lookup failed: {e}")
    return str(user_id)[:8]


class ConversationLogger:
    """Buffers conversation events and flushes to JSON files periodically."""

    def __init__(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        user_name: str,
        conv_id: str,
    ):
        self.agent_id = agent_id
        self.user_id = user_id
        self.user_name = _sanitize_filename(user_name)
        self.conv_id = conv_id
        self._buffer: list[dict[str, Any]] = []
        self._unflushed_count: int = 0
        self._flush_task: asyncio.Task | None = None
        self._closed: bool = False
        self._conv_dir: Path | None = None

    async def start(self) -> None:
        self._conv_dir = WORKSPACE_ROOT / str(self.agent_id) / CONVERSATIONS_DIR
        self._conv_dir.mkdir(parents=True, exist_ok=True)
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def log_user_message(self, content: str) -> None:
        try:
            entry = {
                "role": "user",
                "content": _truncate(content, MAX_MESSAGE_CHARS),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._buffer.append(entry)
            self._unflushed_count += 1
            await self._check_threshold_flush()
        except Exception as e:
            logger.warning(f"[ConvLogger] log_user_message failed: {e}")

    async def log_assistant_message(self, content: str) -> None:
        try:
            entry = {
                "role": "assistant",
                "content": _truncate(content, MAX_MESSAGE_CHARS),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._buffer.append(entry)
            self._unflushed_count += 1
            await self._check_threshold_flush()
        except Exception as e:
            logger.warning(f"[ConvLogger] log_assistant_message failed: {e}")

    async def log_tool_call(
        self,
        tool_name: str,
        args: dict | None = None,
        result: str | None = None,
    ) -> None:
        try:
            entry = {
                "role": "tool_call",
                "tool_name": tool_name,
                "args_summary": _truncate(json.dumps(args or {}, ensure_ascii=False), MAX_ARGS_CHARS),
                "result_summary": _truncate(result or "", MAX_TOOL_RESULT_CHARS),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._buffer.append(entry)
            self._unflushed_count += 1
            await self._check_threshold_flush()
        except Exception as e:
            logger.warning(f"[ConvLogger] log_tool_call failed: {e}")

    async def flush(self) -> None:
        if self._closed or not self._buffer:
            return
        try:
            entries_to_flush = self._buffer[:]
            self._buffer.clear()
            self._unflushed_count = 0
            await asyncio.to_thread(self._write_to_file, entries_to_flush)
        except Exception as e:
            logger.error(f"[ConvLogger] Flush failed for {self.user_name}: {e}")
            self._buffer.extend(entries_to_flush)

    async def close(self) -> None:
        self._closed = True
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    # ── Private ────────────────────────────────────────────────

    async def _periodic_flush(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
                await self.flush()
        except asyncio.CancelledError:
            return

    async def _check_threshold_flush(self) -> None:
        if self._unflushed_count >= FLUSH_THRESHOLD_MESSAGES:
            await self.flush()
        # Cap buffer to prevent unbounded growth
        if len(self._buffer) > MAX_BUFFER_SIZE:
            dropped = len(self._buffer) - MAX_BUFFER_SIZE
            self._buffer = self._buffer[-MAX_BUFFER_SIZE:]
            logger.warning(f"[ConvLogger] Buffer capped, dropped {dropped} oldest entries")

    def _file_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._conv_dir / f"{self.user_name}_{today}.json"

    def _write_to_file(self, entries: list[dict]) -> None:
        path = self._file_path()
        # Ensure directory exists (in case of date change crossing midnight)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing: list[dict] = []
        if path.exists():
            try:
                raw = path.read_text(encoding="utf-8")
                existing = json.loads(raw)
                if not isinstance(existing, list):
                    existing = []
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.extend(entries)
        path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
