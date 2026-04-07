"""Memory compressor - Compresses conversation history using LLM."""

from datetime import datetime, timezone
from typing import Optional
from loguru import logger

from app.services.memory.token_counter import estimate_messages_tokens

COMPRESS_PROMPT = """你是一个对话摘要助手。请将以下对话历史压缩成简洁但完整的摘要。

## 待压缩的对话
{conversation}

## 要求
1. 提取关键信息：用户意图、重要决策、已完成的操作、工具调用结果
2. 如果有未完成的任务或待处理的工具调用，明确列出"待处理事项"
3. 保留具体的名称、数字、文件名、URL 等关键细节（这些信息对后续对话至关重要）
4. 摘要控制在 800 字以内
5. 使用清晰的列表形式组织内容
6. 重点保留"做了什么"和"发现了什么"，省略中间过程细节

## 输出格式
直接输出摘要内容，不要解释。"""

MAX_SUMMARY_CHARS = 9000


class MemoryCompressor:
    """Compresses conversation history using LLM."""

    def detect_pending_tool_calls(self, messages: list[dict]) -> list[dict]:
        """Find tool calls without matching results."""
        call_ids, result_ids = set(), set()
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    call_ids.add(tc.get("id"))
            if msg.get("role") == "tool":
                result_ids.add(msg.get("tool_call_id"))

        pending_ids = call_ids - result_ids
        return [
            {"id": tc.get("id"), "name": tc.get("function", {}).get("name"),
             "args": tc.get("function", {}).get("arguments")}
            for msg in messages
            if msg.get("role") == "assistant" and msg.get("tool_calls")
            for tc in msg["tool_calls"]
            if tc.get("id") in pending_ids
        ]

    def split_for_compression(
        self, messages: list[dict], preserve_count: int,
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Split into (to_compress, tool_context, recent) by message count.

        Args:
            messages: All conversation messages.
            preserve_count: Approximate number of recent messages to keep.

        Returns:
            (to_compress, tool_context, recent)
        """
        if not messages:
            return [], [], []

        # Check for pending tool sequences — these must be kept intact
        pending = self.detect_pending_tool_calls(messages)
        if pending:
            pending_ids = {p["id"] for p in pending}
            boundary = next(
                (i for i, m in enumerate(messages)
                 if m.get("role") == "assistant" and m.get("tool_calls")
                 and {tc.get("id") for tc in m["tool_calls"]} & pending_ids),
                -1,
            )
            if boundary >= 0:
                tool_ctx = messages[boundary:]
                older = messages[:boundary]
                if not older:
                    return [], tool_ctx, []
                # Adjust preserve_count for tool context messages already kept
                adjusted = max(3, preserve_count - len(tool_ctx))
                split_idx = max(0, len(older) - adjusted)
                return older[:split_idx], tool_ctx, older[split_idx:]

        # Normal split: keep last N messages, compress the rest
        split_idx = max(0, len(messages) - preserve_count)
        return messages[:split_idx], [], messages[split_idx:]

    async def compress(
        self, messages: list[dict], llm_client, model: str = None,
    ) -> Optional[str]:
        """Compress messages into a summary via LLM."""
        if not messages:
            return None

        text = self._format_conversation(messages)
        if not text:
            return None

        try:
            prompt = COMPRESS_PROMPT.format(conversation=text)
            result = await self._call_llm(llm_client, prompt, model)
            if result:
                if len(result) > MAX_SUMMARY_CHARS:
                    result = result[:MAX_SUMMARY_CHARS] + "\n...(已截断)"
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                return f"### 对话摘要 ({ts})\n\n{result}"
            return None
        except Exception as e:
            logger.error(f"[Memory] Compression failed: {e}")
            return None

    def _format_conversation(self, messages: list[dict]) -> str:
        """Format messages as readable text for LLM."""
        lines = []
        for msg in messages:
            role, content = msg.get("role", ""), msg.get("content", "") or ""
            if len(content) > 1000:
                content = content[:1000] + "..."

            if role == "user":
                lines.append(f"[用户]: {content}")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    tools = [
                        f"{tc.get('function', {}).get('name', '?')}({tc.get('function', {}).get('arguments', '')[:100]})"
                        for tc in msg["tool_calls"]
                    ]
                    lines.append(f"[助手]: 调用工具: {', '.join(tools)}")
                else:
                    lines.append(f"[助手]: {content}")
            elif role == "tool":
                lines.append(f"[工具结果]: {content}")
        return "\n\n".join(lines)

    async def _call_llm(self, llm_client, prompt: str, model: str = None) -> Optional[str]:
        """Call LLM using project's LLMClient.complete() interface."""
        if llm_client is None:
            return None

        try:
            from app.services.llm_client import LLMMessage

            llm_messages = [LLMMessage(role="user", content=prompt)]
            resp = await llm_client.complete(
                llm_messages,
                max_tokens=1500,
                temperature=0.3,
            )
            if resp and resp.content:
                return resp.content.strip()
            return None
        except Exception as e:
            logger.error(f"[Memory] LLM call failed: {e}")
            return None
