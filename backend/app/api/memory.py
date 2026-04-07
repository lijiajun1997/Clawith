"""Memory system API endpoints.

Token-based configuration:
- GET/PUT /memory/system-config - Company config
- GET/PUT/DELETE /memory/agents/{id}/config - Agent override
- GET /memory/agents/{id}/status - Current status
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.llm import LLMModel
from app.models.memory import (
    MemorySystemConfig,
    AgentMemoryConfig,
)
from app.services.memory.config import (
    get_effective_memory_config,
    DEFAULT_COMPRESS_THRESHOLD,
    DEFAULT_PRESERVE_RATIO,
)

router = APIRouter(prefix="/memory", tags=["memory"])


# === Request/Response Models ===

class MemorySystemConfigUpdate(BaseModel):
    """Request body for company memory config."""
    context_window_tokens: int = Field(
        default=200000,
        ge=32000,
        le=2000000,
        description="Context window size in tokens (e.g., 128000 for 128k, 200000 for 200k)"
    )
    compress_threshold: float = Field(
        default=DEFAULT_COMPRESS_THRESHOLD,
        ge=0.5,
        le=0.95,
        description="Trigger compression at this percentage of context window"
    )
    preserve_ratio: float = Field(
        default=DEFAULT_PRESERVE_RATIO,
        ge=0.1,
        le=0.5,
        description="Keep this percentage of recent messages during compression"
    )


class AgentMemoryConfigUpdate(BaseModel):
    """Request body for agent memory override."""
    context_window_tokens: Optional[int] = Field(
        default=None,
        ge=32000,
        le=2000000,
        description="Override context window (None = inherit from company)"
    )
    compress_threshold: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=0.95,
        description="Override compression threshold"
    )
    preserve_ratio: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=0.5,
        description="Override preserve ratio"
    )


# === Company-level Config ===

@router.get("/system-config")
async def get_memory_system_config(
    tenant_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get company-level memory configuration.

    Fallback: tenant-specific → global → defaults.
    """
    config = None

    # Try tenant-specific first
    if tenant_id:
        query = select(MemorySystemConfig).where(
            MemorySystemConfig.tenant_id == tenant_id
        )
        result = await db.execute(query)
        config = result.scalar_one_or_none()

    # Fallback to global config
    if not config:
        query = select(MemorySystemConfig).where(
            MemorySystemConfig.tenant_id.is_(None)
        )
        result = await db.execute(query)
        config = result.scalar_one_or_none()

    if not config:
        return {
            "exists": False,
            "config": MemorySystemConfigUpdate().model_dump(),
        }

    return {
        "exists": True,
        "config": {
            "id": str(config.id),
            "tenant_id": str(config.tenant_id) if config.tenant_id else None,
            "context_window_tokens": config.context_window_tokens,
            "compress_threshold": config.compress_threshold,
            "preserve_ratio": config.preserve_ratio,
        },
    }


@router.put("/system-config")
async def update_memory_system_config(
    data: MemorySystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update company-level memory configuration."""
    if current_user.role not in ("super_admin", "platform_admin", "org_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Find existing config
    query = select(MemorySystemConfig).where(MemorySystemConfig.tenant_id.is_(None))
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if config:
        config.context_window_tokens = data.context_window_tokens
        config.compress_threshold = data.compress_threshold
        config.preserve_ratio = data.preserve_ratio
    else:
        config = MemorySystemConfig(
            context_window_tokens=data.context_window_tokens,
            compress_threshold=data.compress_threshold,
            preserve_ratio=data.preserve_ratio,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return {"success": True, "id": str(config.id)}


# === Agent-level Config ===

@router.get("/agents/{agent_id}/config")
async def get_agent_memory_config(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent's memory configuration."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get model info for display (no auto-mapping)
    model_provider = None
    model_name = None

    if agent.primary_model_id:
        model = await db.get(LLMModel, agent.primary_model_id)
        if model:
            model_provider = model.provider
            model_name = model.model

    effective_config = await get_effective_memory_config(
        agent_id, db, model_provider, model_name
    )

    # Get company config
    sys_query = select(MemorySystemConfig).where(
        MemorySystemConfig.tenant_id == agent.tenant_id
    )
    sys_result = await db.execute(sys_query)
    sys_config = sys_result.scalar_one_or_none()

    # Get agent config
    agent_query = select(AgentMemoryConfig).where(AgentMemoryConfig.agent_id == agent_id)
    agent_result = await db.execute(agent_query)
    agent_config = agent_result.scalar_one_or_none()

    global_config = {}
    if sys_config:
        global_config = {
            "context_window_tokens": sys_config.context_window_tokens,
            "compress_threshold": sys_config.compress_threshold,
            "preserve_ratio": sys_config.preserve_ratio,
        }

    agent_config_dict = {}
    if agent_config:
        agent_config_dict = {
            "context_window_tokens": agent_config.context_window_tokens,
            "compress_threshold": agent_config.compress_threshold,
            "preserve_ratio": agent_config.preserve_ratio,
        }

    return {
        "model_info": {
            "provider": model_provider,
            "model": model_name,
        },
        "global_config": global_config,
        "agent_config": agent_config_dict,
        "merged_config": {
            "context_window_tokens": effective_config.context_window_tokens,
            "compress_threshold": effective_config.compress_threshold,
            "preserve_ratio": effective_config.preserve_ratio,
            "trigger_tokens": effective_config.trigger_tokens,
            "preserve_tokens": effective_config.preserve_tokens,
        },
    }


@router.put("/agents/{agent_id}/config")
async def update_agent_memory_config(
    agent_id: uuid.UUID,
    data: AgentMemoryConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update agent's memory config override."""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    query = select(AgentMemoryConfig).where(AgentMemoryConfig.agent_id == agent_id)
    result = await db.execute(query)
    config = result.scalar_one_or_none()

    if not config:
        config = AgentMemoryConfig(agent_id=agent_id)
        db.add(config)

    if data.context_window_tokens is not None:
        config.context_window_tokens = data.context_window_tokens
    if data.compress_threshold is not None:
        config.compress_threshold = data.compress_threshold
    if data.preserve_ratio is not None:
        config.preserve_ratio = data.preserve_ratio

    await db.commit()
    return {"success": True}


@router.delete("/agents/{agent_id}/config")
async def reset_agent_memory_config(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset agent config to inherit from company."""
    stmt = delete(AgentMemoryConfig).where(AgentMemoryConfig.agent_id == agent_id)
    await db.execute(stmt)
    await db.commit()
    return {"success": True}


# === Status ===

@router.get("/agents/{agent_id}/status")
async def get_memory_status(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agent's memory status.

    Note: This returns config info only. Actual token counting
    happens during conversation in websocket.py.
    """
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get model info
    model_provider = None
    model_name = None
    if agent.primary_model_id:
        model = await db.get(LLMModel, agent.primary_model_id)
        if model:
            model_provider = model.provider
            model_name = model.model

    config = await get_effective_memory_config(
        agent_id, db, model_provider, model_name
    )

    return {
        "config": {
            "context_window_tokens": config.context_window_tokens,
            "compress_threshold": config.compress_threshold,
            "preserve_ratio": config.preserve_ratio,
            "trigger_tokens": config.trigger_tokens,
            "preserve_tokens": config.preserve_tokens,
        },
    }
