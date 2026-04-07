"""Memory system configuration.

Token-based config:
- context_window_tokens: Context window size, user-configured (default 200k)
- compress_threshold: Trigger compression at X% (default 0.75)
- preserve_ratio: Keep recent X% of messages (default 0.25)

Note: No model auto-mapping. Users must manually configure context window size.
"""

from dataclasses import dataclass
import uuid
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemorySystemConfig, AgentMemoryConfig
from app.models.agent import Agent

# === Defaults ===
DEFAULT_CONTEXT_WINDOW = 200_000
DEFAULT_COMPRESS_THRESHOLD = 0.75
DEFAULT_PRESERVE_RATIO = 0.25


@dataclass
class MemoryConfig:
    """Effective memory configuration."""
    context_window_tokens: int = DEFAULT_CONTEXT_WINDOW
    compress_threshold: float = DEFAULT_COMPRESS_THRESHOLD
    preserve_ratio: float = DEFAULT_PRESERVE_RATIO

    @property
    def trigger_tokens(self) -> int:
        """Token count at which compression triggers."""
        return int(self.context_window_tokens * self.compress_threshold)

    @property
    def preserve_tokens(self) -> int:
        """Token budget for messages to keep."""
        return int(self.context_window_tokens * self.preserve_ratio)

    @property
    def preserve_message_count(self) -> int:
        """Rough message count to preserve (~100 tokens/msg avg)."""
        return max(3, self.preserve_tokens // 100)


def _first(*values):
    """Return first non-None value."""
    for v in values:
        if v is not None:
            return v
    return None


async def get_effective_memory_config(
    agent_id: uuid.UUID,
    db: AsyncSession,
    model_provider: str = None,
    model_name: str = None,
) -> MemoryConfig:
    """Get effective config. Priority: Agent > Company > Default (200k).

    No model auto-mapping — users configure context window manually.
    """
    agent = await db.get(Agent, agent_id)
    if not agent:
        return MemoryConfig()

    # Company config (tenant-specific > global)
    sys_stmt = select(MemorySystemConfig).where(
        or_(
            MemorySystemConfig.tenant_id == agent.tenant_id,
            MemorySystemConfig.tenant_id.is_(None),
        )
    ).order_by(MemorySystemConfig.tenant_id.desc())
    sys_cfg = (await db.execute(sys_stmt)).scalar_one_or_none()

    # Agent override
    ag_stmt = select(AgentMemoryConfig).where(AgentMemoryConfig.agent_id == agent_id)
    ag_cfg = (await db.execute(ag_stmt)).scalar_one_or_none()

    return MemoryConfig(
        context_window_tokens=_first(
            ag_cfg.context_window_tokens if ag_cfg else None,
            sys_cfg.context_window_tokens if sys_cfg else None,
        ) or DEFAULT_CONTEXT_WINDOW,
        compress_threshold=_first(
            ag_cfg.compress_threshold if ag_cfg else None,
            sys_cfg.compress_threshold if sys_cfg else None,
        ) or DEFAULT_COMPRESS_THRESHOLD,
        preserve_ratio=_first(
            ag_cfg.preserve_ratio if ag_cfg else None,
            sys_cfg.preserve_ratio if sys_cfg else None,
        ) or DEFAULT_PRESERVE_RATIO,
    )
