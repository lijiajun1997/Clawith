"""Company configuration synchronization service.

Periodically syncs company-level prompts (system prompt, heartbeat instruction)
from TenantSetting to all agent workspaces.
"""

import asyncio
import uuid
from pathlib import Path
from loguru import logger
from sqlalchemy import select
from app.config import get_settings
from app.models.tenant_setting import TenantSetting
from app.models.agent import Agent
from app.database import async_session

settings = get_settings()
PERSISTENT_DATA = Path(settings.AGENT_DATA_DIR)

# Configuration keys in TenantSetting
KEY_SYSTEM_PROMPT = "company_system_prompt"
KEY_HEARTBEAT_INSTRUCTION = "company_heartbeat_instruction"

# Target filenames in agent workspace
FILE_SYSTEM_PROMPT = "COMPANY_SYSTEM_PROMPT.md"
FILE_HEARTBEAT_INSTRUCTION = "COMPANY_HEARTBEAT.md"


async def sync_company_config_to_agent(agent_id: uuid.UUID, config: dict) -> bool:
    """Sync company configuration to a single agent workspace.

    Args:
        agent_id: Agent UUID
        config: Dictionary with keys from KEY_SYSTEM_PROMPT and KEY_HEARTBEAT_INSTRUCTION

    Returns:
        True if at least one file was written, False otherwise
    """
    ws_root = PERSISTENT_DATA / str(agent_id)
    if not ws_root.exists():
        return False

    written = False

    # Write system prompt
    if KEY_SYSTEM_PROMPT in config and config[KEY_SYSTEM_PROMPT]:
        content = config[KEY_SYSTEM_PROMPT]
        if content.strip():
            file_path = ws_root / FILE_SYSTEM_PROMPT
            try:
                file_path.write_text(content, encoding="utf-8")
                written = True
            except Exception as e:
                logger.warning(f"[CompanyConfigSync] Failed to write {FILE_SYSTEM_PROMPT} for agent {agent_id}: {e}")

    # Write heartbeat instruction
    if KEY_HEARTBEAT_INSTRUCTION in config and config[KEY_HEARTBEAT_INSTRUCTION]:
        content = config[KEY_HEARTBEAT_INSTRUCTION]
        if content.strip():
            file_path = ws_root / FILE_HEARTBEAT_INSTRUCTION
            try:
                file_path.write_text(content, encoding="utf-8")
                written = True
            except Exception as e:
                logger.warning(f"[CompanyConfigSync] Failed to write {FILE_HEARTBEAT_INSTRUCTION} for agent {agent_id}: {e}")

    return written


async def get_tenant_config(tenant_id: uuid.UUID) -> dict:
    """Get company configuration from TenantSetting.

    Returns:
        Dictionary with config content, keys: KEY_SYSTEM_PROMPT, KEY_HEARTBEAT_INSTRUCTION
    """
    config = {}

    async with async_session() as db:
        result = await db.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id,
                TenantSetting.key.in_([KEY_SYSTEM_PROMPT, KEY_HEARTBEAT_INSTRUCTION])
            )
        )
        settings_records = result.scalars().all()

        for record in settings_records:
            if record.value and "content" in record.value:
                config[record.key] = record.value["content"]

    return config


async def sync_all_agents_for_tenant(tenant_id: uuid.UUID, config: dict) -> int:
    """Sync configuration to all agents in a tenant.

    Args:
        tenant_id: Tenant UUID
        config: Configuration dictionary

    Returns:
        Number of agents updated
    """
    async with async_session() as db:
        result = await db.execute(
            select(Agent).where(Agent.tenant_id == tenant_id)
        )
        agents = result.scalars().all()

        updated = 0
        for agent in agents:
            if await sync_company_config_to_agent(agent.id, config):
                updated += 1

        if updated > 0:
            logger.info(f"[CompanyConfigSync] Synced config to {updated} agents in tenant {tenant_id}")

        return updated


async def _sync_tick():
    """One sync tick: check for tenant config changes and sync to agents."""
    try:
        async with async_session() as db:
            # Get all tenants with company config settings
            result = await db.execute(
                select(TenantSetting).where(
                    TenantSetting.key.in_([KEY_SYSTEM_PROMPT, KEY_HEARTBEAT_INSTRUCTION])
                )
            )
            settings_records = result.scalars().all()

            # Group by tenant_id
            tenant_configs = {}
            for record in settings_records:
                tenant_id = record.tenant_id
                if tenant_id not in tenant_configs:
                    tenant_configs[tenant_id] = {}
                if record.value and "content" in record.value:
                    tenant_configs[tenant_id][record.key] = record.value["content"]

            # Sync to agents for each tenant
            total_updated = 0
            for tenant_id, config in tenant_configs.items():
                updated = await sync_all_agents_for_tenant(tenant_id, config)
                total_updated += updated

            if total_updated > 0:
                logger.info(f"[CompanyConfigSync] Synced company config to {total_updated} agents total")

    except Exception as e:
        logger.exception(f"[CompanyConfigSync] Sync tick error: {e}")


async def start_company_config_sync():
    """Start the background company config sync service."""
    logger.info("[CompanyConfigSync] Service started (5min interval)")

    while True:
        await _sync_tick()
        await asyncio.sleep(300)  # 5 minutes
