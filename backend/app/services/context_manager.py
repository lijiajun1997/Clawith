"""Token-aware context management for LLM conversations.

Tracks cumulative token usage per session using Redis,
triggers background compression at 80% threshold,
and provides tool-call-aware history management.

Design principles (inspired by CoPaw):
- Compression only modifies DB, never the in-memory api_messages list
- Summary is injected as a prepended user message (no schema changes)
- All new features are opt-in: context_window_size=NULL → legacy message-count mode
- Background compression is fire-and-forget with Redis lock
"""

import asyncio
import json
from datetime import datetime, timezone

from loguru import logger

# ── Constants ──────────────────────────────────────────────

_COMPRESS_RATIO = 0.80  # Trigger compression at 80% of context window
_HARD_LIMIT_RATIO = 0.95  # Synchronous fallback at 95%
_COMPRESS_TARGET = 0.60  # Compress the oldest 60% of messages
_PRESERVED_TOOL_ROUNDS = 5  # Keep last N tool rounds in full detail
_MAX_TOOL_CALL_RECORDS = 50  # Max tool_call messages in history summary

# Redis key patterns
_CTX_STATE_KEY = "ctx:state:{agent_id}:{session_id}"
_CTX_SUMMARY_KEY = "ctx:summary:{agent_id}:{session_id}"
_CTX_LOCK_KEY = "ctx:lock:{agent_id}:{session_id}"

# Compression prompts
_INITIAL_COMPRESS_PROMPT = """你是对话压缩引擎。将以下对话历史压缩为结构化摘要，严格保留：
- 已执行的工具调用及关键结果（文件路径、URL、数据值）
- 关键决策及其原因
- 正在进行的任务和待完成的工作
- 用户偏好和明确指令
- 重要数据、名称、日期

输出格式（Markdown）：
## 目标
...
## 已完成的工作
...
## 关键工具调用记录
- read_file("path/to/file") → 文件包含...
- write_file("path/to/file", ...) → 写入成功
## 进行中的任务
...
## 重要上下文
...

不要添加评论或元文本。直接输出摘要。"""

_UPDATE_COMPRESS_PROMPT = """你是对话压缩引擎。请将新增对话的关键信息融合到已有摘要中。

已有摘要：
{existing_summary}

新增对话：
{new_conversation}

保持原摘要格式一致，补充新信息，更新已变化的状态。直接输出合并后的摘要。"""


# ── Token extraction ───────────────────────────────────────

def extract_prompt_tokens(usage: dict | None) -> int | None:
    """Extract the prompt/input token count from an LLM response usage dict.

    This is the precise measurement of how many tokens the current context consumes.
    OpenAI format: prompt_tokens, Anthropic format: input_tokens.
    """
    if not usage:
        return None
    return usage.get("prompt_tokens") or usage.get("input_tokens")


# ── Known context windows (fallback when DB field is NULL) ──

_KNOWN_WINDOWS: dict[str, int] = {
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4.1": 1_000_000,
    "o3": 200_000,
    "o4-mini": 200_000,
    "deepseek-chat": 64_000,
    "deepseek-reasoner": 64_000,
    "gemini-2.5-pro": 1_000_000,
    "gemini-2.5-flash": 1_000_000,
    "qwen-long": 1_000_000,
}


def get_effective_context_window(model) -> int | None:
    """Resolve the effective context window size in tokens.

    Priority: model.context_window_size > known model prefix lookup > None
    """
    # DB field takes precedence
    ctx = getattr(model, "context_window_size", None)
    if ctx and ctx > 0:
        return ctx

    # Fallback: match by model name prefix
    model_name = getattr(model, "model", "") or ""
    for prefix, window in _KNOWN_WINDOWS.items():
        if model_name.startswith(prefix):
            return window

    return None


# ── Redis helpers ──────────────────────────────────────────

async def _get_redis():
    from app.core.events import get_redis
    return await get_redis()


async def record_session_tokens(agent_id: str, session_id: str,
                                 prompt_tokens: int, model_window: int) -> dict | None:
    """Update the running token state for a session in Redis."""
    try:
        r = await _get_redis()
        key = _CTX_STATE_KEY.format(agent_id=agent_id, session_id=session_id)
        state = {"prompt_tokens": prompt_tokens, "window": model_window,
                 "updated_at": datetime.now(timezone.utc).isoformat()}
        await r.set(key, json.dumps(state), ex=3600)
        return state
    except Exception as e:
        logger.warning(f"[CtxMgr] Failed to record session tokens: {e}")
        return None


# ── Compression trigger ────────────────────────────────────

async def maybe_trigger_compression(
    agent_id, session_id: str,
    prompt_tokens: int, model_window: int,
    agent_name: str, role_description: str,
    model, fallback_model=None,
) -> bool:
    """Check threshold and fire background compression if needed.

    Returns True if compression was triggered, False otherwise.
    Non-blocking: creates an asyncio.Task and returns immediately.
    """
    # Normalize agent_id to string for consistent Redis keys
    agent_id = str(agent_id)

    if prompt_tokens < model_window * _COMPRESS_RATIO:
        return False

    logger.info(f"[CtxMgr] Threshold reached: {prompt_tokens}/{model_window} tokens "
                f"({prompt_tokens/model_window:.0%}), triggering background compression")

    # Record state for the background task to read
    await record_session_tokens(str(agent_id), session_id, prompt_tokens, model_window)

    # Acquire lock to prevent duplicate compression
    try:
        r = await _get_redis()
        lock_key = _CTX_LOCK_KEY.format(agent_id=agent_id, session_id=session_id)
        locked = await r.set(lock_key, "1", nx=True, ex=300)
        if not locked:
            logger.info(f"[CtxMgr] Compression already in progress, skipping")
            return False
    except Exception as e:
        logger.warning(f"[CtxMgr] Redis lock failed, skipping compression: {e}")
        return False

    # Fire and forget
    asyncio.create_task(_do_compress(
        agent_id, session_id, agent_name, role_description, model, fallback_model
    ))
    return True


# ── Hard limit: synchronous truncation at 95% ─────────────

async def emergency_truncate(agent_id, session_id: str, prompt_tokens: int, model_window: int) -> int:
    """Synchronous fallback when background compression didn't complete in time.

    Deletes the oldest 60% of DB messages for this session to free token budget.
    Returns the number of messages deleted.

    This is a safety net: it loses information but prevents API errors from
    exceeding the model's context window.
    """
    agent_id = str(agent_id)
    logger.warning(f"[CtxMgr] HARD LIMIT at {prompt_tokens}/{model_window} tokens "
                   f"({prompt_tokens/model_window:.0%}) — emergency truncating history")

    try:
        from app.database import async_session
        from app.models.audit import ChatMessage
        from sqlalchemy import select, delete as sql_delete

        async with async_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.agent_id == agent_id,
                       ChatMessage.conversation_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            all_messages = list(result.scalars().all())

            if len(all_messages) < 4:
                logger.warning("[CtxMgr] Too few messages to truncate")
                return 0

            # Keep the newest 40%, delete the oldest 60% (at round boundary)
            split_idx = _find_split_boundary(all_messages)
            older_ids = [m.id for m in all_messages[:split_idx]]

            await db.execute(
                sql_delete(ChatMessage).where(ChatMessage.id.in_(older_ids))
            )
            await db.commit()

            logger.warning(f"[CtxMgr] Emergency truncation: deleted {len(older_ids)} oldest messages, "
                           f"kept {len(all_messages) - len(older_ids)} recent ones")
            return len(older_ids)

    except Exception as e:
        logger.error(f"[CtxMgr] Emergency truncation failed: {e}")
        return 0


# ── Background compression execution ──────────────────────

async def _do_compress(
    agent_id, session_id: str,
    agent_name: str, role_description: str,
    model, fallback_model=None,
) -> None:
    """Run compression in background. Modifies DB, signals via Redis."""
    lock_key = _CTX_LOCK_KEY.format(agent_id=agent_id, session_id=session_id)
    summary_key = _CTX_SUMMARY_KEY.format(agent_id=agent_id, session_id=session_id)

    try:
        from app.database import async_session
        from app.models.audit import ChatMessage
        from sqlalchemy import select, delete as sql_delete

        # 1. Load all messages for this session
        async with async_session() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.agent_id == agent_id,
                       ChatMessage.conversation_id == session_id)
                .order_by(ChatMessage.created_at.asc())
            )
            all_messages = list(result.scalars().all())

        if len(all_messages) < 10:
            logger.info(f"[CtxMgr] Too few messages ({len(all_messages)}), skipping compression")
            return

        # 2. Split at a conversation round boundary
        split_idx = _find_split_boundary(all_messages)
        older_messages = all_messages[:split_idx]
        # recent_messages kept in DB as-is

        # 3. Format older messages for compression
        older_text = _format_messages_for_compression(older_messages)
        if not older_text.strip():
            logger.info(f"[CtxMgr] No content to compress")
            return

        # 4. Check for existing summary (incremental vs initial)
        r = await _get_redis()
        existing_summary = await r.get(summary_key)
        if isinstance(existing_summary, bytes):
            existing_summary = existing_summary.decode("utf-8")

        # 5. Call LLM for compression
        compressed = await _compress_via_llm(
            older_text, model, agent_id, existing_summary=existing_summary
        )

        if not compressed or not compressed.strip():
            logger.warning(f"[CtxMgr] Compression returned empty result, aborting")
            return

        # 6. Store summary in Redis for injection on next user message
        await r.set(summary_key, compressed, ex=7200)  # 2h TTL

        # 7. Delete compressed messages from DB
        async with async_session() as db:
            older_ids = [m.id for m in older_messages]
            await db.execute(
                sql_delete(ChatMessage).where(ChatMessage.id.in_(older_ids))
            )
            await db.commit()

        logger.info(f"[CtxMgr] Compression complete: {len(older_messages)} messages "
                    f"→ summary ({len(compressed)} chars)")

    except Exception as e:
        logger.error(f"[CtxMgr] Compression failed: {e}", exc_info=True)
    finally:
        # Release lock
        try:
            r = await _get_redis()
            await r.delete(lock_key)
        except Exception:
            pass


def _find_split_boundary(all_messages: list, target_ratio: float = _COMPRESS_TARGET) -> int:
    """Find a safe split index that respects conversation round boundaries.

    A round is: user [+ tool_call(s)] + assistant.
    We only split before a 'user' message so that:
    - No orphaned tool_call rows (their user/assistant context is kept)
    - No broken tool_call → assistant pairs

    Returns the index to split at (all_messages[:split] = to compress/delete).
    """
    target_idx = int(len(all_messages) * target_ratio)

    # Walk backward from target to find the nearest user message boundary
    for i in range(target_idx, max(target_idx - 20, 0), -1):
        if all_messages[i].role == "user":
            return i

    # Walk forward from target
    for i in range(target_idx, min(target_idx + 20, len(all_messages))):
        if all_messages[i].role == "user":
            return i

    # Fallback: use raw ratio (last resort)
    return target_idx


def _format_messages_for_compression(messages) -> str:
    """Format DB ChatMessage objects into text for LLM compression."""
    parts = []
    for msg in messages:
        role = msg.role or "unknown"
        content = msg.content or ""
        # Truncate very long individual messages to keep compression input manageable
        if len(content) > 3000:
            from app.utils.text import truncate_head_tail
            content = truncate_head_tail(content, 3000, tail_chars=500)
        if role == "tool_call":
            try:
                tc = json.loads(content)
                name = tc.get("name", "?")
                args = tc.get("args", {})
                result = tc.get("result", "")
                status = tc.get("status", "done")
                args_str = json.dumps(args, ensure_ascii=False)[:200]
                result_str = result[:300] if result else ""
                parts.append(f"[Tool] {name}({args_str}) => {result_str} [{status}]")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"[Tool] {content[:200]}")
        elif role == "user":
            parts.append(f"[User] {content}")
        elif role == "assistant":
            parts.append(f"[Assistant] {content[:2000]}")
        elif role == "system":
            # Skip system messages — they're rebuilt each time
            continue
    return "\n\n".join(parts)


async def _compress_via_llm(
    older_text: str, model, agent_id,
    existing_summary: str | None = None,
) -> str | None:
    """Call the LLM to compress conversation history into a summary."""
    try:
        from app.services.llm_utils import create_llm_client, get_model_api_key, LLMMessage
    except ImportError:
        logger.error("[CtxMgr] Cannot import LLM utilities")
        return None

    client = None
    try:
        api_key = get_model_api_key(model)
        client = create_llm_client(
            provider=model.provider,
            api_key=api_key,
            model=model.model,
            base_url=model.base_url,
            timeout=120.0,
        )

        if existing_summary:
            prompt = _UPDATE_COMPRESS_PROMPT.format(
                existing_summary=existing_summary,
                new_conversation=older_text,
            )
        else:
            prompt = _INITIAL_COMPRESS_PROMPT + "\n\n对话历史：\n" + older_text

        messages = [
            LLMMessage(role="system", content="你是一个精确的对话压缩引擎。只输出结构化摘要，不添加任何评论。"),
            LLMMessage(role="user", content=prompt),
        ]

        response = await client.complete(
            messages=messages,
            temperature=0.3,
            max_tokens=8000,
        )
        return response.content

    except Exception as e:
        logger.error(f"[CtxMgr] LLM compression call failed: {e}")
        return None
    finally:
        if client:
            try:
                await client.close()
            except Exception:
                pass


# ── Summary injection ──────────────────────────────────────

async def check_inject_summary(
    agent_id: str, session_id: str,
    conversation: list[dict],
) -> list[dict]:
    """Check if a compression summary is available and inject it into the conversation.

    Called from websocket_chat() after building the conversation history.
    Injects the summary as a prepended user message (no DB schema change needed).
    """
    try:
        r = await _get_redis()
        summary_key = _CTX_SUMMARY_KEY.format(agent_id=agent_id, session_id=session_id)
        raw = await r.get(summary_key)
        if not raw:
            return conversation

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        # Consume the summary (delete after reading)
        await r.delete(summary_key)

        # Inject as the first user message in conversation
        summary_msg = {
            "role": "user",
            "content": f"以下是之前对话的压缩摘要，用于保持上下文连续性：\n\n{raw}",
        }

        logger.info(f"[CtxMgr] Injecting compression summary ({len(raw)} chars) into conversation")
        return [summary_msg] + conversation

    except Exception as e:
        logger.warning(f"[CtxMgr] Failed to inject summary: {e}")
        return conversation


# ── Graduated tool call summary (Safety 2) ─────────────────

def build_graduated_tool_summary(
    tool_calls: list[dict],
) -> str:
    """Build a tool call summary with graduated detail levels.

    - Last 5 rounds: full detail (result preserved with head+tail)
    - Next 45 (up to index 50): moderate detail (result truncated to 300 chars)
    - Beyond 50: single-line summary (100 chars max)

    Args:
        tool_calls: List of tool_call dicts in chronological order.
            Each has: name, args, result, status
    """
    if not tool_calls:
        return ""

    from app.utils.text import truncate_head_tail

    total = len(tool_calls)
    parts = ["[Previous tool calls in this session:]"]

    # Define boundaries (from the end, since recent = more detail)
    preserved_end = total  # exclusive end index
    preserved_start = max(0, total - _PRESERVED_TOOL_ROUNDS)
    moderate_start = max(0, total - _MAX_TOOL_CALL_RECORDS)

    for i, tc in enumerate(tool_calls):
        name = tc.get("name", "unknown")
        args = tc.get("args", {})
        result = tc.get("result", "")
        status = tc.get("status", "done")

        if isinstance(args, dict):
            args_str = ", ".join(
                f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"
                for k, v in args.items()
            )
        else:
            args_str = str(args)

        if i >= preserved_start:
            # Last 5 rounds: full detail
            result_preview = truncate_head_tail(result or "", 600, tail_chars=200)
            parts.append(f"  - Called {name}({args_str}) => {result_preview}")
        elif i >= moderate_start:
            # 6th~50th: moderate detail
            result_preview = truncate_head_tail(result or "", 300, tail_chars=120)
            parts.append(f"  - Called {name}({args_str}) => {result_preview}")
        else:
            # Beyond 50: minimal summary
            args_brief = args_str[:80]
            result_brief = (result or "")[:100]
            parts.append(f"  - {name}({args_brief}) => {result_brief}")

    return "\n".join(parts)


# ── In-memory context overflow protection ──────────────────
# These functions operate on the in-memory api_messages list directly,
# complementing the DB-level compression above.  They are the safety net
# that prevents exceed_context_size_error during long tool-calling loops.

_MAX_TOOL_RESULT_CHARS = 50_000  # Single tool result max chars (~16k tokens)
_TRIM_THRESHOLD_RATIO = 0.85    # Trigger in-memory trim at 85% of window
_TRIM_TARGET_RATIO = 0.55       # After trimming, target 55% of window


def estimate_messages_tokens(messages: list) -> int:
    """Fast token estimate for an in-memory LLMMessage list.

    Uses the ~3 chars/token heuristic.  Iterates each message's text
    fields and sums character counts, then converts.

    Returns 0 on any failure (safe — downstream will skip trimming).
    """
    try:
        total_chars = 0
        for m in messages:
            c = getattr(m, "content", None)
            if isinstance(c, str):
                total_chars += len(c)
            elif isinstance(c, list):
                for part in c:
                    if isinstance(part, dict):
                        txt = part.get("text", "")
                        if isinstance(txt, str):
                            total_chars += len(txt)

            dc = getattr(m, "dynamic_content", None)
            if isinstance(dc, str):
                total_chars += len(dc)

            rc = getattr(m, "reasoning_content", None)
            if isinstance(rc, str):
                total_chars += len(rc)

            tcs = getattr(m, "tool_calls", None)
            if tcs and isinstance(tcs, list):
                for tc in tcs:
                    fn = tc.get("function", {})
                    total_chars += len(fn.get("name", ""))
                    total_chars += len(fn.get("arguments", ""))

        return max(total_chars // 3, 1)
    except Exception:
        return 0


def truncate_tool_result(content: str | list, max_chars: int = _MAX_TOOL_RESULT_CHARS) -> str | list:
    """Truncate a tool result string to prevent single-output token bloat.

    Preserves list (vision) content unchanged — vision payloads are gated
    by the model's image handling, not text token limits.

    Returns original content unchanged on any error.
    """
    try:
        if not content:
            return content
        if isinstance(content, list):
            return content
        if not isinstance(content, str):
            return content
        if len(content) <= max_chars:
            return content
        from app.utils.text import truncate_head_tail
        truncated = truncate_head_tail(content, max_chars, tail_chars=2000)
        return truncated + f"\n\n[tool result truncated from {len(content)} to {max_chars} chars]"
    except Exception:
        return content


def trim_api_messages_inplace(
    api_messages: list,
    prompt_tokens: int | None,
    model_window: int,
) -> int:
    """In-place trim of an in-memory LLMMessage list when it risks
    exceeding the model's context window.

    This is the memory-level safety net that complements the DB-level
    compression in maybe_trigger_compression / emergency_truncate.

    Strategy:
      1. Estimate current token usage (prefer real prompt_tokens from
         API response, fall back to char-based estimate).
      2. If usage < 85% of window → no-op (return 0).
      3. If usage >= 85% → remove oldest messages between index 1 (system
         prompt at index 0 is always preserved) and a calculated split point.
      4. Fix sequence integrity: drop orphaned tool messages whose parent
         assistant+tool_calls was removed.

    Returns the number of messages removed.  Returns 0 on any error.

    IMPORTANT: mutates api_messages in-place via slice assignment.
    """
    try:
        if not api_messages or model_window <= 0:
            return 0
        if len(api_messages) <= 3:
            return 0  # system + user + assistant — too few to trim

        # Step 1: estimate current usage
        if prompt_tokens and prompt_tokens > 0:
            current_tokens = prompt_tokens
        else:
            current_tokens = estimate_messages_tokens(api_messages)

        if current_tokens <= 0:
            return 0

        threshold = int(model_window * _TRIM_THRESHOLD_RATIO)
        if current_tokens < threshold:
            return 0  # Below danger zone — no-op

        logger.warning(
            f"[CtxMgr] In-memory trim triggered: ~{current_tokens} tokens "
            f"vs {model_window} window ({current_tokens / model_window:.0%}). "
            f"Messages: {len(api_messages)}"
        )

        original_len = len(api_messages)

        # Step 2: calculate how many messages to remove
        target_tokens = int(model_window * _TRIM_TARGET_RATIO)
        avg_tokens_per_msg = max(current_tokens / len(api_messages), 1)
        excess_tokens = max(current_tokens - target_tokens, 0)
        msgs_to_remove = max(int(excess_tokens / avg_tokens_per_msg), 1)

        # Never remove the system prompt (index 0).
        # Never remove the last 4 messages (recent context + current tool round).
        min_preserve_tail = 4
        max_removable = len(api_messages) - 1 - min_preserve_tail
        msgs_to_remove = min(msgs_to_remove, max_removable)
        if msgs_to_remove <= 0:
            return 0

        # Remove oldest messages after system prompt
        del api_messages[1 : 1 + msgs_to_remove]

        # Step 3: fix sequence integrity — drop orphaned messages
        # Pass 1: drop orphaned tool messages
        _fixed = [api_messages[0]]  # keep system prompt
        for i in range(1, len(api_messages)):
            m = api_messages[i]
            if m.role == "tool":
                tc_ids = set()
                if _fixed and _fixed[-1].role == "assistant" and _fixed[-1].tool_calls:
                    tc_ids = {tc.get("id", "") for tc in _fixed[-1].tool_calls}
                if m.tool_call_id and m.tool_call_id in tc_ids:
                    _fixed.append(m)
                # else: orphaned tool — skip
            else:
                _fixed.append(m)

        # Pass 2: drop assistant+tool_calls with no following tool responses
        _cleaned = []
        for j in range(len(_fixed)):
            m = _fixed[j]
            if m.role == "assistant" and m.tool_calls:
                tc_ids = {tc.get("id", "") for tc in m.tool_calls}
                has_response = any(
                    _fixed[k].role == "tool" and _fixed[k].tool_call_id in tc_ids
                    for k in range(j + 1, min(j + 1 + len(m.tool_calls) * 2, len(_fixed)))
                )
                if has_response:
                    _cleaned.append(m)
                # else: orphaned assistant with tool_calls — drop
            else:
                _cleaned.append(m)

        # Replace contents in-place so caller's reference stays valid
        removed_count = original_len - len(_cleaned)
        api_messages[:] = _cleaned

        logger.info(
            f"[CtxMgr] In-memory trim complete: removed {removed_count} messages, "
            f"{len(api_messages)} remaining"
        )
        return max(removed_count, 0)

    except Exception as e:
        logger.error(f"[CtxMgr] In-memory trim failed (safe fallback): {e}")
        return 0
