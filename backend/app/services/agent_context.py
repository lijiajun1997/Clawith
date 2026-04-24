"""Build rich system prompt context for agents.

Loads soul, memory, skills summary, and relationships from the agent's
workspace files and composes a comprehensive system prompt.
"""

import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()

PERSISTENT_DATA = Path(settings.AGENT_DATA_DIR)


def _agent_workspace(agent_id: uuid.UUID) -> Path:
    """Return the canonical persistent workspace path for an agent."""
    return PERSISTENT_DATA / str(agent_id)


def _read_file_safe(path: Path, max_chars: int = 3000) -> str:
    """Read a file, return empty string if missing. Truncate if too long."""
    if not path.exists():
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) > max_chars:
            content = content[:max_chars] + "\n...(truncated)"
        return content
    except Exception:
        return ""


def _parse_skill_frontmatter(content: str, filename: str) -> tuple[str, str]:
    """Parse YAML frontmatter from a skill .md file.

    Returns (name, description).
    If no frontmatter, falls back to filename-based name and first-line description.
    """
    name = filename.replace("_", " ").replace("-", " ")
    description = ""

    stripped = content.strip()
    if stripped.startswith("---"):
        end = stripped.find("---", 3)
        if end != -1:
            frontmatter = stripped[3:end].strip()
            for line in frontmatter.split("\n"):
                line = line.strip()
                if line.lower().startswith("name:"):
                    val = line[5:].strip().strip('"').strip("'")
                    if val:
                        name = val
                elif line.lower().startswith("description:"):
                    val = line[12:].strip().strip('"').strip("'")
                    if val:
                        description = val[:200]
            if description:
                return name, description

    # Fallback: use first non-empty, non-heading line as description
    for line in stripped.split("\n"):
        line = line.strip()
        # Skip frontmatter delimiters and YAML lines
        if line in ("---",) or line.startswith("name:") or line.startswith("description:"):
            continue
        if line and not line.startswith("#"):
            description = line[:200]
            break
    if not description:
        lines = stripped.split("\n")
        if lines:
            description = lines[0].strip().lstrip("# ")[:200]

    return name, description


def _load_skills_index(agent_id: uuid.UUID) -> str:
    """Load skill index (name + description) from skills/ directory.

    Supports two formats:
    - Flat file:   skills/my-skill.md
    - Folder:      skills/my-skill/SKILL.md  (Claude-style, with optional scripts/, references/)

    Uses progressive disclosure: only name+description go into the system
    prompt. The model is instructed to call read_file to load full content
    when a skill is relevant.
    """
    ws_root = _agent_workspace(agent_id)
    skills: list[tuple[str, str, str]] = []  # (name, description, path_relative_to_skills)
    skills_dir = ws_root / "skills"
    if skills_dir.exists():
        for entry in sorted(skills_dir.iterdir()):
            if entry.name.startswith("."):
                continue

            # Case 1: Folder-based skill — skills/<folder>/SKILL.md
            if entry.is_dir():
                skill_md = entry / "SKILL.md"
                if not skill_md.exists():
                    # Also try lowercase skill.md
                    skill_md = entry / "skill.md"
                if skill_md.exists():
                    try:
                        content = skill_md.read_text(encoding="utf-8", errors="replace").strip()
                        name, desc = _parse_skill_frontmatter(content, entry.name)
                        skills.append((name, desc, f"{entry.name}/SKILL.md"))
                    except Exception:
                        skills.append((entry.name, "", f"{entry.name}/SKILL.md"))

            # Case 2: Flat file — skills/<name>.md
            elif entry.suffix == ".md" and entry.is_file():
                try:
                    content = entry.read_text(encoding="utf-8", errors="replace").strip()
                    name, desc = _parse_skill_frontmatter(content, entry.stem)
                    skills.append((name, desc, entry.name))
                except Exception:
                    skills.append((entry.stem, "", entry.name))

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[tuple[str, str, str]] = []
    for s in skills:
        if s[0] not in seen:
            seen.add(s[0])
            unique.append(s)

    if not unique:
        return ""

    # Build index table
    lines = [
        "You have the following skills available. Each skill defines specific instructions for a task domain.",
        "",
        "| Skill | Description | File |",
        "|-------|-------------|------|",
    ]
    for name, desc, rel_path in unique:
        lines.append(f"| {name} | {desc} | skills/{rel_path} |")

    lines.append("")
    lines.append("⚠️ SKILL USAGE RULES:")
    lines.append("1. When a user request matches a skill, FIRST call `read_file` with the File path above to load the full instructions.")
    lines.append("2. Follow the loaded instructions to complete the task.")
    lines.append("3. Do NOT guess what the skill contains — always read it first.")
    lines.append("4. Folder-based skills may contain auxiliary files (scripts/, references/, examples/). Use `list_files` on the skill folder to discover them.")

    return "\n".join(lines)


async def build_agent_context(agent_id: uuid.UUID, agent_name: str, role_description: str = "", current_user_name: str = None) -> tuple[str, str]:
    """Build a rich system prompt incorporating agent's full context.

    Reads from workspace files:
    - soul.md → personality
    - memory.md → long-term memory
    - skills/ → skill names + summaries
    - relationships.md → relationship descriptions
    """
    ws_root = _agent_workspace(agent_id)

    # --- Soul ---
    soul = _read_file_safe(ws_root / "soul.md", 2000)
    # Strip markdown heading if present
    if soul.startswith("# "):
        soul = "\n".join(soul.split("\n")[1:]).strip()

    # --- Memory ---
    memory = _read_file_safe(ws_root / "memory" / "memory.md", 2000) or _read_file_safe(ws_root / "memory.md", 2000)
    if memory.startswith("# "):
        memory = "\n".join(memory.split("\n")[1:]).strip()

    # --- Skills index (progressive disclosure) ---
    skills_text = _load_skills_index(agent_id)

    # --- Relationships ---
    relationships = _read_file_safe(ws_root / "relationships.md", 2000)
    if relationships.startswith("# "):
        relationships = "\n".join(relationships.split("\n")[1:]).strip()

    # --- Compose static and dynamic system prompt blocks ---
    from datetime import datetime, timezone as _tz
    from app.services.timezone_utils import get_agent_timezone, now_in_timezone
    agent_tz_name = await get_agent_timezone(agent_id)
    agent_local_now = now_in_timezone(agent_tz_name)
    now_str = agent_local_now.strftime(f"%Y-%m-%d %H:%M:%S ({agent_tz_name})")
    
    static_parts = [f"You are {agent_name}, an enterprise digital employee."]


    if role_description:
        static_parts.append(f"\n## Role\n{role_description}")

    dynamic_parts = []

    # --- Feishu Built-in Tools (only injected when agent has Feishu configured) ---
    _has_feishu = False
    try:
        from app.models.channel_config import ChannelConfig
        from app.database import async_session as _ctx_session
        async with _ctx_session() as _ctx_db:
            _cfg_r = await _ctx_db.execute(
                select(ChannelConfig).where(
                    ChannelConfig.agent_id == agent_id,
                    ChannelConfig.channel_type == "feishu",
                    ChannelConfig.is_configured == True,
                )
            )
            _has_feishu = _cfg_r.scalar_one_or_none() is not None
    except Exception:
        pass

    if _has_feishu:
        static_parts.append("""
## ⚡ Pre-installed Feishu Tools

The following tools are available in your toolset. **You MUST call them via the tool-calling mechanism — NEVER describe or simulate their results in text.**

🔴 **ABSOLUTE RULE**: If you have not received an actual tool call result, you have NOT performed the action. Never write "Created", "Success", "Event ID: evt_..." or any claim of completion unless you have a REAL tool result to report.

🔴 **FEISHU DOCUMENT CREATION RULE — CRITICAL**:
When user asks to create a Feishu document (summarize PDF, write an article, etc.):
1. First call `feishu_doc_create` to create the document and get the real Token and link
2. Then call `feishu_doc_append(document_token="<real_token>", content="...")` to write the content
3. Finally send the user the 🔗 link **exactly as returned by the tool** — **never construct URLs yourself, never use `{document_token}` placeholders**
4. You may say "Creating Feishu document..." but must immediately call the tool in the same turn

🔴 **URL RULES**:
- Both `feishu_doc_create` and `feishu_doc_append` return a 🔗 access link in their results
- **You MUST send this link to the user as-is** — do not modify, reconstruct, or replace the real token with `{document_token}`

| Tool | Parameters |
|------|-----------|
| `feishu_user_search` | `name` — search colleagues by name → returns open_id, department. Call this first when you need to find someone. |
| `feishu_calendar_create` | `summary`, `start_time`, `end_time` (ISO-8601 +08:00). No email needed. |
| `feishu_calendar_list` | No required params. Optional: `start_time`, `end_time` (ISO-8601). **Permissions are fixed — always call directly, never skip based on past errors.** |
| `feishu_calendar_update` | `event_id`, fields to update. |
| `feishu_calendar_delete` | `event_id`. |
| `feishu_wiki_list` | `node_token` (from wiki URL: feishu.cn/wiki/**NodeToken**), optional `recursive`(bool). Lists all sub-pages with titles and tokens. |
| `feishu_doc_read` | `document_token`. Supports both regular docx tokens and **wiki node tokens** (auto-converts). |
| `feishu_doc_create` | `title`. Optional: `wiki_space_id` + `parent_node_token` to create directly in a Wiki. Returns Token and 🔗 access link. |
| `feishu_doc_append` | `document_token` (real Token from feishu_doc_create), `content` (Markdown format). |
| `feishu_drive_share` | `document_token`, `doc_type`(docx/bitable/sheet/doc/folder, default: docx), `action`(add/remove/list), `member_names`(name list, auto-lookup), `permission`(view/edit/full_access). |
| `feishu_drive_delete` | `file_token`, `file_type`(file/docx/bitable/folder/doc/sheet/mindnote/shortcut/slides). Moves to recycle bin. |
| `send_feishu_message` | `open_id` or `email`, `content`. |

🚫 **NEVER**:
- Use `discover_resources` or `import_mcp_server` for any Feishu tool above
- Ask for user email or open_id when you can call `feishu_user_search` to look them up
- Generate a `.ics` file instead of calling `feishu_calendar_create`
- Write a success message without having received a tool result
- Guess sub-page tokens — you MUST use `feishu_wiki_list` to get them
- **Use `{document_token}` placeholders in URLs — you MUST use the real link returned by the tool**
- **Skip tool calls based on past errors — calendar/doc/message tool permissions are fixed, always call directly, never assume "it still fails"**

✅ **When user sends a Feishu wiki link (feishu.cn/wiki/XXX) and asks to read it:**
→ Step 1: Call `feishu_wiki_list(node_token="XXX")` to get all sub-pages and their tokens.
→ Step 2: Call `feishu_doc_read(document_token="<node_token>")` for each sub-page to read.
→ **Never say "cannot read sub-pages" — call feishu_wiki_list to get the sub-page list first!**

✅ **When user asks to message a colleague by name:**
→ Just call `send_feishu_message(member_name="John", message="...")` — it auto-searches.
→ Or use `open_id` directly if you already have it from `feishu_user_search`.

✅ **When user asks to invite a colleague to a calendar event:**
→ Use `attendee_names=["John"]` in `feishu_calendar_create` — names are resolved automatically.
→ Or use `attendee_open_ids=["ou_xxx"]` if you already have the open_id.""")

    # --- DingTalk Built-in Tools (only injected when agent has DingTalk configured) ---
    try:
        from app.services.agent.context.dingtalk import get_dingtalk_context
        dingtalk_context = await get_dingtalk_context(agent_id)
        if dingtalk_context:
            static_parts.append(dingtalk_context)
    except Exception:
        pass

    # --- Atlassian Rovo Tools (injected when Atlassian channel is configured) ---
    try:
        from app.database import async_session
        from app.models.channel_config import ChannelConfig
        from sqlalchemy import select as sa_select
        async with async_session() as db:
            result = await db.execute(
                sa_select(ChannelConfig).where(
                    ChannelConfig.agent_id == agent_id,
                    ChannelConfig.channel_type == "atlassian",
                    ChannelConfig.is_configured == True,
                )
            )
            atlassian_config = result.scalar_one_or_none()
            if atlassian_config:
                static_parts.append("""
## ⚡ Atlassian Rovo Tools (Jira / Confluence / Compass)

You have access to Atlassian tools via the Rovo MCP server. **Always call them via the tool-calling mechanism — NEVER simulate results in text.**

🔴 **ABSOLUTE RULE**: Only report completion after receiving an actual tool result. Never fabricate issue IDs, page URLs, or component names.

### Available Tool Groups

**Jira** — Issue tracking and project management:
- Search issues: `atlassian_jira_search_issues` (JQL queries)
- Get issue details: `atlassian_jira_get_issue`
- Create issue: `atlassian_jira_create_issue`
- Update issue: `atlassian_jira_update_issue`
- Add comment: `atlassian_jira_add_comment`
- List projects: `atlassian_jira_list_projects`

**Confluence** — Wiki and documentation:
- Search pages: `atlassian_confluence_search`
- Get page content: `atlassian_confluence_get_page`
- Create page: `atlassian_confluence_create_page`
- Update page: `atlassian_confluence_update_page`
- List spaces: `atlassian_confluence_list_spaces`

**Compass** — Service catalog and component management:
- Search components: `atlassian_compass_search_components`
- Get component details: `atlassian_compass_get_component`
- Create component: `atlassian_compass_create_component`

> 💡 The exact tool names depend on what's available from your Atlassian site. Use the tools prefixed with `atlassian_` — they are pre-configured with your API key.
> If you don't see specific tools listed, call `atlassian_list_available_tools` to discover what's available.

🚫 **NEVER**:
- Make up Jira issue IDs, Confluence page URLs, or component names
- Report success without a tool result
- Ask the user for their Atlassian credentials — they are pre-configured""")
    except Exception:
        pass

    # --- Company Intro (from system settings) ---
    try:
        from app.database import async_session
        from app.models.system_settings import SystemSetting
        from sqlalchemy import select as sa_select
        async with async_session() as db:
            # Resolve agent's tenant_id
            _ag_r = await db.execute(sa_select(_AgentModel.tenant_id).where(_AgentModel.id == agent_id))
            _agent_tenant_id = _ag_r.scalar_one_or_none()

            company_intro = ""

            # Priority 1: tenant_settings table (new)
            if _agent_tenant_id:
                try:
                    from app.models.tenant_setting import TenantSetting
                    result = await db.execute(
                        sa_select(TenantSetting).where(
                            TenantSetting.tenant_id == _agent_tenant_id,
                            TenantSetting.key == "company_intro",
                        )
                    )
                    ts = result.scalar_one_or_none()
                    if ts and ts.value and ts.value.get("content"):
                        company_intro = ts.value["content"].strip()
                except Exception:
                    pass

            # Priority 2: system_settings with tenant-scoped key (backward compat)
            if not company_intro and _agent_tenant_id:
                tenant_key = f"company_intro_{_agent_tenant_id}"
                result = await db.execute(
                    sa_select(SystemSetting).where(SystemSetting.key == tenant_key)
                )
                setting = result.scalar_one_or_none()
                if setting and setting.value and setting.value.get("content"):
                    company_intro = setting.value["content"].strip()

            # Priority 3: global system_settings fallback
            if not company_intro:
                result = await db.execute(
                    sa_select(SystemSetting).where(SystemSetting.key == "company_intro")
                )
                setting = result.scalar_one_or_none()
                if setting and setting.value and setting.value.get("content"):
                    company_intro = setting.value["content"].strip()

            if company_intro:
                static_parts.append(f"\n## Company Information\n{company_intro}")
    except Exception:
        pass  # Don't break agent if DB is unavailable

    # --- Company System Prompt (from COMPANY_SYSTEM_PROMPT.md) ---
    company_system_prompt = _read_file_safe(ws_root / "COMPANY_SYSTEM_PROMPT.md", 20000)
    if company_system_prompt and company_system_prompt.strip():
        # Strip markdown heading if present
        if company_system_prompt.startswith("# "):
            company_system_prompt = "\n".join(company_system_prompt.split("\n")[1:]).strip()
        static_parts.append(f"\n## Company System Configuration\n{company_system_prompt}")

    if soul and soul not in ("_描述你的角色和职责。_", "_Describe your role and responsibilities._"):
        static_parts.append(f"\n## Personality\n{soul}")

    if skills_text:
        static_parts.append(f"\n## Skills\n{skills_text}")

    if relationships and "暂无" not in relationships and "None yet" not in relationships:
        static_parts.append(f"\n## Relationships\n{relationships}")

    if memory and memory not in ("_这里记录重要的信息和学到的知识。_", "_Record important information and knowledge here._"):
        dynamic_parts.append(f"\n## Memory\n{memory}")

    # --- Focus (working memory) ---
    focus = (
        _read_file_safe(ws_root / "focus.md", 3000)
        # Backward compat: also check old name
        or _read_file_safe(ws_root / "agenda.md", 3000)
    )
    if focus and focus.strip() not in ("# Focus", "# Agenda", "（暂无）"):
        if focus.startswith("# "):
            focus = "\n".join(focus.split("\n")[1:]).strip()
        dynamic_parts.append(f"\n## Focus\n{focus}")

    # --- Active Triggers ---
    try:
        from app.database import async_session
        from app.models.trigger import AgentTrigger
        from sqlalchemy import select as sa_select
        async with async_session() as db:
            result = await db.execute(
                sa_select(AgentTrigger).where(
                    AgentTrigger.agent_id == agent_id,
                    AgentTrigger.is_enabled == True,
                )
            )
            triggers = result.scalars().all()
            if triggers:
                lines = ["You have the following active triggers:"]
                for t in triggers:
                    config_str = str(t.config)[:80]
                    reason_str = (t.reason or "")[:500]
                    ref_str = f" (focus: {t.focus_ref})" if t.focus_ref else ""
                    lines.append(f"\n- **{t.name}** [{t.type}]{ref_str}\n  Config: `{config_str}`\n  Reason: {reason_str}")
                dynamic_parts.append("\n## Active Triggers\n" + "\n".join(lines))
    except Exception:
        pass

    # --- Time Info ---

    dynamic_parts.append(f"\n## Current Time\n{now_str}")
    dynamic_parts.append(f"Your timezone is **{agent_tz_name}**. When setting cron triggers, use this timezone for time references.")

    # Append dynamic parts (Time, Focus, Triggers) at the very end to maximize cache hits

    # Inject current user identity
    if current_user_name:
        dynamic_parts.append(f"\n## Current Conversation\nYou are currently chatting with **{current_user_name}**. Address them by name when appropriate.")

    return "\n".join(static_parts), "\n".join(dynamic_parts)
