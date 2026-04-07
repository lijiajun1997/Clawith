"""Memory manager - Token-based conversation compression.

Trigger: token usage >= threshold% of context window.
Action: compress older messages into LLM summary, keep recent messages by count.
"""

import uuid
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.config import MemoryConfig
from app.services.memory.token_counter import estimate_messages_tokens
from app.services.memory.compressor import MemoryCompressor
from app.models.memory import CompressionSummary


class MemoryManager:
    """Manages conversation memory with token-based compression."""

    def __init__(self, agent_id: uuid.UUID, config: Optional[MemoryConfig] = None):
        self.agent_id = agent_id
        self._config = config or MemoryConfig()
        self.compressor = MemoryCompressor()
        self._busy = False

    def should_compress(self, messages: list[dict]) -> bool:
        """Check if compression should trigger."""
        if self._busy or not messages:
            return False
        current = estimate_messages_tokens(messages)
        trigger = self._config.trigger_tokens
        logger.info(
            f"[Memory] check: {current} tokens >= {trigger} trigger? "
            f"(ctx={self._config.context_window_tokens}, "
            f"thresh={self._config.compress_threshold}) "
            f"| msgs={len(messages)} | busy={self._busy}"
        )
        return current >= trigger

    async def compress_messages(
        self,
        messages: list[dict],
        llm_client,
        model: str = None,
        db: AsyncSession = None,
        session_id: str = None,
    ) -> tuple[Optional[str], list[dict]]:
        """Compress messages, return (summary, remaining).

        Uses approximate message count (preserve_message_count) instead of
        strict token locking, for simpler and more predictable behavior.

        Returns (None, original_messages) if not needed or failed.
        """
        if self._busy:
            return None, messages

        if not self.should_compress(messages):
            return None, messages

        self._busy = True
        try:
            to_compress, tool_ctx, recent = self.compressor.split_for_compression(
                messages, self._config.preserve_message_count,
            )

            if not to_compress:
                return None, messages

            logger.info(
                f"[Memory] Compressing {len(to_compress)} msgs "
                f"({estimate_messages_tokens(to_compress)} tokens) for {self.agent_id}"
            )

            summary = await self.compressor.compress(to_compress, llm_client, model)

            if not summary:
                return None, messages

            # Persist summary
            if db:
                try:
                    db.add(CompressionSummary(
                        agent_id=self.agent_id,
                        session_id=session_id,
                        summary_text=summary,
                        original_token_count=estimate_messages_tokens(to_compress),
                        summary_token_count=estimate_messages_tokens(
                            [{"role": "user", "content": summary}]
                        ),
                    ))
                    await db.commit()
                except Exception as e:
                    logger.warning(f"[Memory] Failed to store summary: {e}")

            remaining = recent + tool_ctx
            logger.info(f"[Memory] Done. Kept {len(remaining)} msgs")
            return summary, remaining

        except Exception as e:
            logger.error(f"[Memory] Compression failed: {e}")
            return None, messages
        finally:
            self._busy = False

    async def get_stored_summaries(
        self, db: AsyncSession, session_id: str = None, limit: int = 5,
    ) -> list[str]:
        """Get stored compression summaries."""
        query = select(CompressionSummary).where(
            CompressionSummary.agent_id == self.agent_id
        )
        if session_id:
            query = query.where(CompressionSummary.session_id == session_id)
        query = query.order_by(CompressionSummary.created_at.desc()).limit(limit)

        result = await db.execute(query)
        return [s.summary_text for s in result.scalars().all()]
