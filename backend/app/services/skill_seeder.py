"""Seed builtin skills into the global skill registry."""

from loguru import logger
from sqlalchemy import select
from app.database import async_session
from app.models.skill import Skill, SkillFile


BUILTIN_SKILLS = [
    {
        "name": "Web Research",
        "description": "Systematic web searching and information synthesis. Use when: needing factual data from the web, evaluating sources, or cross-referencing claims. NOT for: simple trivia or local file search.",
        "category": "research",
        "icon": "🔍",
        "folder_name": "web-research",
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: Web Research
description: Systematic web searching, source evaluation, and information synthesis
---

# Web Research

## Overview
Use this skill when you need to find, evaluate, and synthesize information from the web.

**Keywords**: web search, information retrieval, source evaluation, fact-checking, research

## Process

### 1. Define Search Strategy
- Identify key search terms and variations
- Consider different angles and perspectives
- Plan multiple search queries

### 2. Evaluate Sources
- Check source credibility and recency
- Cross-reference claims across multiple sources
- Note publication dates and author expertise

### 3. Synthesize Findings
- Organize information by theme or relevance
- Highlight key findings and consensus views
- Note conflicting information and gaps

## Output Format
- Start with a brief summary of findings
- Provide detailed sections with source citations
- End with confidence assessment and limitations
""",
            },
            {
                "path": "scripts/search_helper.py",
                "content": (
                    "#!/usr/bin/env python3\n"
                    '"""Helper utilities for structured web search."""\n\n'
                    "from datetime import datetime\n\n\n"
                    "def format_search_results(results: list[dict]) -> str:\n"
                    '    """Format raw search results into a structured report."""\n'
                    "    output = []\n"
                    "    for i, r in enumerate(results, 1):\n"
                    "        title = r.get('title', 'Untitled')\n"
                    "        url = r.get('url', '#')\n"
                    "        snippet = r.get('snippet', 'No description')\n"
                    "        output.append(f'{i}. [{title}]({url})')\n"
                    "        output.append(f'   {snippet}')\n"
                    "        output.append('')\n"
                    "    return '\\n'.join(output)\n\n\n"
                    "def assess_source_credibility(url: str) -> dict:\n"
                    '    """Basic heuristics for source credibility."""\n'
                    "    trusted = ['.edu', '.gov', '.org', 'arxiv.org', 'nature.com']\n"
                    "    score = 0.5\n"
                    "    for d in trusted:\n"
                    "        if d in url:\n"
                    "            score = 0.8\n"
                    "            break\n"
                    "    return {'url': url, 'credibility_score': score,\n"
                    "            'assessed_at': datetime.now().isoformat()}\n"
                ),
            },
        ],
    },
    {
        "name": "Data Analysis",
        "description": "Data interpretation and structured reporting. Use when: analyzing CSV/dataset files, finding trends, or generating statistical summaries. NOT for: writing code to build data models.",
        "category": "analysis",
        "icon": "📊",
        "folder_name": "data-analysis",
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: Data Analysis
description: Data interpretation, pattern recognition, and structured reporting
---

# Data Analysis

## Overview
Use this skill for analyzing data, identifying patterns, and creating structured reports.

**Keywords**: data analysis, statistics, trends, visualization, reporting

## Process

### 1. Data Understanding
- Identify data types, ranges, and distributions
- Check for missing values and anomalies
- Understand the business context

### 2. Analysis Methods
- Descriptive statistics (mean, median, distribution)
- Trend analysis (time-series patterns)
- Comparative analysis (benchmarking, A/B)
- Correlation and relationship discovery

### 3. Reporting
- Lead with key insights and actionable findings
- Use tables and structured formats for clarity
- Include methodology notes for reproducibility

## Output Format
- Executive summary with top 3 findings
- Detailed analysis with supporting data
- Recommendations based on findings
""",
            },
            {
                "path": "scripts/analyze_csv.py",
                "content": (
                    "#!/usr/bin/env python3\n"
                    '"""Utility for quick CSV data analysis."""\n\n'
                    "import csv\nimport statistics\nfrom collections import Counter\n\n\n"
                    "def analyze_column(data: list[dict], column: str) -> dict:\n"
                    '    """Analyze a single column from CSV data."""\n'
                    "    values = [row.get(column) for row in data if row.get(column) is not None]\n"
                    "    if not values:\n"
                    '        return {"column": column, "count": 0, "error": "No data"}\n\n'
                    '    result = {"column": column, "count": len(values), "unique": len(set(values))}\n\n'
                    "    # Try numeric analysis\n"
                    "    try:\n"
                    "        nums = [float(v) for v in values]\n"
                    "        result.update({\n"
                    '            "type": "numeric",\n'
                    '            "min": min(nums), "max": max(nums),\n'
                    '            "mean": round(statistics.mean(nums), 2),\n'
                    '            "median": round(statistics.median(nums), 2),\n'
                    "        })\n"
                    "    except (ValueError, TypeError):\n"
                    "        freq = Counter(values).most_common(5)\n"
                    '        result.update({"type": "categorical", "top_values": freq})\n\n'
                    "    return result\n\n\n"
                    "def quick_summary(filepath: str) -> str:\n"
                    '    """Generate a quick summary of a CSV file."""\n'
                    "    with open(filepath, 'r') as f:\n"
                    "        reader = csv.DictReader(f)\n"
                    "        data = list(reader)\n"
                    "    columns = data[0].keys() if data else []\n"
                    "    return f'Rows: {len(data)}, Columns: {len(columns)}'\n"
                ),
            },
            {
                "path": "examples/sample_report.md",
                "content": """# Sample Analysis Report

## Executive Summary
Analysis of Q4 2024 sales data reveals a 12% increase in total revenue,
driven primarily by the Enterprise segment (+23%).

## Key Findings
1. **Revenue Growth**: Total revenue increased from $2.1M to $2.35M
2. **Top Segment**: Enterprise accounts grew 23% QoQ
3. **Churn**: SMB churn rate decreased from 5.2% to 4.1%

## Detailed Analysis

| Metric | Q3 2024 | Q4 2024 | Change |
|--------|---------|---------|--------|
| Total Revenue | $2.1M | $2.35M | +12% |
| Enterprise | $1.2M | $1.47M | +23% |
| SMB | $0.9M | $0.88M | -2% |
| Churn Rate | 5.2% | 4.1% | -1.1pp |

## Recommendations
1. Increase investment in Enterprise sales team
2. Investigate SMB revenue decline
3. Continue churn reduction initiatives
""",
            },
        ],
    },
    {
        "name": "Content Writing",
        "description": "Professional content creation and tone adaptation. Use when: drafting articles, emails, or marketing copy with specific stylistic requirements. NOT for: casual chat responses.",
        "category": "creation",
        "icon": "✍️",
        "folder_name": "content-writing",
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: Content Writing
description: Professional content creation, editing, and tone adaptation
---

# Content Writing

## Overview
Use this skill for creating, editing, and polishing written content across formats.

**Keywords**: writing, editing, copywriting, tone, style, proofreading

## Content Types
- **Articles & Blog Posts**: Informative, engaging long-form content
- **Business Communications**: Emails, memos, reports
- **Marketing Copy**: Headlines, descriptions, calls-to-action
- **Documentation**: Technical docs, guides, FAQs

## Guidelines

### Structure
- Hook readers with a compelling opening
- Use clear headings and logical flow
- Keep paragraphs short (3-5 sentences)
- End with a clear conclusion or call-to-action

### Tone Adaptation
- **Formal**: Business reports, official communications
- **Professional**: Client-facing content, documentation
- **Conversational**: Blog posts, social media
- **Technical**: Developer docs, specifications

### Quality Checklist
- [ ] Clear main message
- [ ] Consistent tone throughout
- [ ] No grammatical errors
- [ ] Appropriate length for format
""",
            },
        ],
    },
    {
        "name": "Competitive Analysis",
        "description": "Competitor research and comparison frameworks. Use when: asked to compare companies, products, or perform SWOT/feature matrix analysis. NOT for: general academic research.",
        "category": "research",
        "icon": "⚔️",
        "folder_name": "competitive-analysis",
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: Competitive Analysis
description: Market competitor research, comparison frameworks, and strategic insights
---

# Competitive Analysis

## Overview
Use this skill for analyzing competitors, market positioning, and strategic opportunities.

**Keywords**: competitors, market analysis, SWOT, positioning, benchmarking

## Frameworks

### SWOT Analysis
| | Helpful | Harmful |
|---|---|---|
| **Internal** | Strengths | Weaknesses |
| **External** | Opportunities | Threats |

### Feature Comparison Matrix
Compare products across key dimensions:
- Core features and capabilities
- Pricing and packaging
- Target audience
- Market positioning
- Technology stack

### Porter's Five Forces
1. Competitive rivalry intensity
2. Bargaining power of suppliers
3. Bargaining power of buyers
4. Threat of new entrants
5. Threat of substitutes

## Output Format
- Competitor overview table
- Detailed per-competitor analysis
- Strategic recommendations
- Key differentiators summary
""",
            },
        ],
    },
    {
        "name": "ProudAI Meeting Notes",
        "description": "Professional meeting minutes for audit/consulting firms. Use when: given meeting transcripts, agendas, or rough notes from audit/internal/QC/BD meetings to produce structured minutes with speaker inference, scenario-based logic, and domain terminology correction. NOT for: generic document summarization or non-business meetings.",
        "category": "productivity",
        "icon": "📝",
        "folder_name": "meeting-notes",
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: ProudAI Meeting Notes
description: Professional meeting minutes expert for audit/consulting firms — structured extraction, speaker inference, scenario-based logic, and domain terminology correction
---

# ProudAI - 智能会议纪要专家

## [Role & Mandate]
你是 **ProudAI**，宝臻/宝格（Prouden/Prouder）的首席会议纪要专家。
你的核心目标是将原始、杂乱的会议输入（议程表+语音转录文本）转化为结构化、高度专业、且极具执行力的**会议纪要（Meeting Minutes）**。

**【最高红线原则 - ZERO TOLERANCE】**
1. **禁止过度记录 (No Over-documenting)**：纪要必须精炼。只提取核心观点、决策和待办事项。剔除所有寒暄、重复论证、情绪化表达和废话。
2. **禁止主观发挥 (No Hallucination/Supplement)**：**绝对不允许**添加会议中未提及的分析、补充背景、商业判断或个人推测。你只是客观信息的提炼者，不是会议的参与者。
注意：影响判断的信息需要先询问用户再撰写，如果没有重要的信息，可以先写，再询问用户哪些点是否需要补充和修改。

## [Module 1: 智能角色推断与发言整合 (Speaker & Entity Inference)]
会议转录往往无法精准区分每一个Speaker（尤其是线上+线下混合会议）。你必须具备"听音辨位"和"归纳阵营"的能力：
1. **身份猜测与映射**：结合上下文语境（如谈论底稿、复核、函证的通常是审计师；谈论业务数据、痛点、审批的通常是客户）。
2. **模糊化与阵营化处理**：如果多个Speaker听起来像是在补充同一个观点，或者名字识别混乱，**不要强行关联具体名字**。请将其概括为**各方/实体观点**。
   * *正确示范*："宝臻团队指出... / 管理层反馈... / 评估师（Third-party）认为... / 审计团队与客户就XX达成共识..."
   * *错误示范*："Speaker 1说... Speaker 2说... 然后Speaker 1又说..."
3. **聚焦负责人**：在讨论观点时可以模糊具体人名，但在提取**待办事项（Action Items）**时，必须尽可能锁定具体的负责人（Owner）或负责团队（如：JS Team, Prouden, 公司财务部）。

---

## [Module 2: 多场景动态总结引擎 (Scenario-Based Logic)]
在处理文本前，先判断会议属于以下哪种场景，并自动调用对应的归纳逻辑：

### 场景 A：审计内部会议 / QC复核 / 项目复盘 (Internal Audit / Post-Mortem)
* **总结逻辑**：以**审计方法论 (Smart Audit)** 和 **审计阶段** 为主线。
* **提取重点**：
  * **Top Mission (M+)** 的决策过程、定性结论与拆解原则 (First Principles)。
  * **TTT (Talk to Top)** 的谈判策略与结果。
  * 审计计划 (Planning)、执行 (Execution)、反舞弊程序 (Anti-fraud) 的核心发现。
  * 底稿简化 (Documentation) 及 避免复核冗余 (Review Efficiency) 的指导意见。

### 场景 B：外部审计推进 / Weekly Update (Audit Execution Sync)
* **总结逻辑**：以 **财务科目 (Accounts)** 或 **责任方 (Parties)** 为主线。
* **提取重点**：
  * 核心科目进展（如：收入确认 Principal vs Agent, 存货 Roll-back/减值, CECL 预期信用损失, Cut-off 截止性测试）。
  * 跨团队协作事项（如：Marcum进展, JS团队底稿, 公司PBC提供进度）。
  * 明确的卡点 (Blockers) 与未决事项 (Pending Issues)。

### 场景 C：BD / 客户提案 / 战略与IPO咨询 (Pitching & Consulting)
* **总结逻辑**：以 **商业模式** 和 **解决路径** 为主线。
* **提取重点**：
  * 客户背景、业务规模与当前痛点（如：缺乏上市统筹人才、特定融资需求）。
  * 宝格/宝臻提供的核心价值主张（如：IPO健康检查、充当总协调人、重塑商业模型）。
  * 下一步商业推进动作（如：签署NDA、提供报价、起草商业计划书/内参报告）。

### 场景 D：行业调研 / 标的筛选 (Industry Research)
* **总结逻辑**：以 **筛选规则** 和 **行业洞察** 为主线。
* **提取重点**：
  * 目标行业、区域、企业性质（如：专精特新、非国有、排除特定行业）。
  * 财务指标基准（如：毛利率要求）。
  * 具体的筛选进展与下一步研究名单（Target List）。

---

## [Module 3: Prouden/Prouder 专属专业词典 (Domain Dictionary)]
**纠错指令**：语音转文字常有同音错别字，遇到以下概念的谐音，必须强制纠正为标准术语：
* **核心方法论 (Smart 2.0)**: Top Mission (重大核心任务/不可写成Top Machine), TMF (项目作战地图), TTT (Talk to Top/顶层沟通), M+ (经理级以上), Deal Breaker.
* **审计高频词**: PBC (客户提供资料), Interim TOD (期中细节测试), CECL (预期信用损失), Roll-back (倒推测试), Cut-off (截止性测试), Principal vs Agent (总额法与净额法), IPE (Information Produced by Entity), FAR (固定资产登记册), JET (分录测试), PAJE (拟调整分录), WCGW (可能出错环节).
* **角色与资质**: EP (合伙人), EQR/QC (质量复核), PL (项目负责人), SIC/MIC (现场高审/经理).

---

## [Module 4: 强制输出格式 (Strict Output Format)]
你必须使用 Markdown 格式输出，且**结构必须如下**（请根据实际场景灵活调整内部的小标题）：

```markdown
# [会议主题/项目名称] - 会议纪要

> **会议时间**：[YYYY/MM/DD] [Time]
> **会议地点/方式**：[Location/Online]
> **参会阵营/人员**：[按实体分类，如：宝格团队：A, B；客户团队：X, Y]

---

### I. 核心摘要 (Executive Summary)
*(根据上述Module 2的场景逻辑，用精炼的语言概括会议背景、最核心的商业结论/审计定性判断。不超过3-5个Bullet points，绝不记流水账。)*
*   **[核心结论 1]**：...
*   **[核心结论 2]**：...

---

### II. 待办与跟进事项 (Action Items) - 核心聚焦
*(提取所有下一步明确要做的动作。如果没有明确到人，落实到团队。务必极度可执行。)*
| 序号 | 责任方 (Owner) | 待办事项内容 (Action) | 备注/截止日期 |
| :--- | :--- | :--- | :--- |
| 1 | [@具体人 或 某团队] | [具体动作，如：提供XX合同 / 完成XX科目底稿 / 发送报价单] | [Time/Memo] |
| 2 | ... | ... | ... |

---

### III. 详细会议记录 (Detailed Minutes)
*(根据Module 2判定的场景，采取适当的分类方式。使用"观点归类法"，用客观、专业的商业/审计中文陈述。禁止逐字稿，禁止流水账。)*

#### [分类维度 1 - 例如：Top Mission / 核心科目 / 业务板块]
*   **当前情况/卡点**: [客观描述]
*   **各方观点/讨论**:
    *   *审计团队/宝格提出*: ...
    *   *管理层/客户反馈*: ...
*   **决议/应对**: [达成的共识或采取的程序]

#### [分类维度 2 - ...]
*   ... 把这个内容融入目前系统自带的skill  skills/meeting-notes/SKILL.md  进行替换
```
""",
            },
        ],
    },
    {
        "name": "Complex Task Executor",
        "description": "Structured methodology for decomposing, planning, and executing complex multi-step tasks with progress tracking",
        "category": "productivity",
        "icon": "🎯",
        "folder_name": "complex-task-executor",
        "is_default": True,
        "files": [
            {
                "path": "SKILL.md",
                "content": """---
name: Complex Task Executor
description: Structured methodology for decomposing, planning, and executing complex multi-step tasks with progress tracking
---

# Complex Task Executor

## When to Use This Skill

Use this skill when a task meets ANY of the following criteria:
- Requires more than 3 distinct steps to complete
- Involves multiple tools or information sources
- Has dependencies between steps (step B needs output from step A)
- Requires research before execution
- Could benefit from a documented plan others can review
- The user explicitly asks for a thorough or systematic approach

**DO NOT use this for simple tasks** like answering a question, reading a single file, or performing one tool call.

## Workflow

### Phase 1: Task Analysis (THINK before acting)

Before creating any files, analyze the task:

1. **Understand the goal**: What is the final deliverable? What does "done" look like?
2. **Assess complexity**: How many steps? What tools are needed?
3. **Identify dependencies**: Which steps depend on others?
4. **Identify risks**: What could go wrong? What information is missing?
5. **Estimate scope**: Is the task feasible with available tools/skills?

### Phase 2: Create Task Plan

Create a task folder and plan file in the workspace:

```
workspace/<task-name>/plan.md
```

The plan.md MUST follow this exact format:

```markdown
# Task: <Clear title>

## Objective
<One-sentence description of the desired outcome>

## Steps

- [ ] 1. <First step — verb-noun format>
  - Details: <What specifically to do>
  - Output: <What this step produces>
- [ ] 2. <Second step>
  - Details: <...>
  - Depends on: Step 1
- [ ] 3. <Third step>
  - Details: <...>

## Status
- Created: <timestamp>
- Current Step: Not started
- Progress: 0/<total>

## Notes
<Any assumptions, risks, or open questions>
```

Rules for writing the plan:
- Each step should be completable in 1-3 tool calls
- Use verb-noun format: "Research competitors", "Draft report", "Validate data"
- Mark dependencies explicitly
- Include expected outputs for each step

### Phase 3: Execute Step-by-Step

For EACH step in the plan:

1. **Read the plan** — Call `read_file` on `workspace/<task>/plan.md` to check current state
2. **Mark as in-progress** — Update the checkbox from `[ ]` to `[/]` and update the "Current Step" field
3. **Execute the step** — Do the actual work (tool calls, analysis, writing)
4. **Record output** — Save results to `workspace/<task>/` (e.g., intermediate files, data)
5. **Mark as complete** — Update the checkbox from `[/]` to `[x]` and update "Progress" counter
6. **Proceed to next step** — Move to the next uncompleted step

### Phase 4: Completion

When all steps are done:
1. Update plan.md status to "✅ Completed"
2. Create a `workspace/<task>/summary.md` with:
   - What was accomplished
   - Key results and deliverables
   - Any follow-up items
3. Present the final result to the user

## Adaptive Replanning

If during execution you discover:
- A step is impossible → Mark it `[!]` with a reason, add alternative steps
- New steps are needed → Add them to the plan with `[+]` prefix
- A step produced unexpected results → Add a note and adjust subsequent steps
- The plan needs major changes → Create a new section "## Revised Plan" and follow it

Always update plan.md BEFORE changing course, so the plan stays the source of truth.

## Error Handling

- If a tool call fails, retry once. If it fails again, mark the step as blocked and note the error.
- Never silently skip a step. Always update the plan to reflect what happened.
- If you're stuck, tell the user what's blocking and ask for guidance.

## Example Scenarios

### Example 1: "Research our top 3 competitors and write a comparison report"

Plan would be:
```
- [ ] 1. Identify the user's company/product context
- [ ] 2. Research Competitor A — website, pricing, features
- [ ] 3. Research Competitor B — website, pricing, features
- [ ] 4. Research Competitor C — website, pricing, features
- [ ] 5. Create comparison matrix
- [ ] 6. Write analysis and recommendations
- [ ] 7. Compile final report
```

### Example 2: "Analyze our Q4 sales data and prepare a board presentation"

Plan would be:
```
- [ ] 1. Read and understand the sales data files
- [ ] 2. Calculate key metrics (revenue, growth, trends)
- [ ] 3. Identify top insights and anomalies
- [ ] 4. Create data summary tables
- [ ] 5. Draft presentation outline
- [ ] 6. Write each presentation section
- [ ] 7. Add executive summary
- [ ] 8. Review and polish final document
```

## Key Principles

1. **Plan is the source of truth** — Always update it before moving on
2. **One step at a time** — Don't skip ahead or batch too many steps
3. **Show your work** — Save intermediate results to the task folder
4. **Communicate progress** — The user can read plan.md at any time to see status
5. **Be adaptive** — Plans change; that's OK if you update the plan first
""",
            },
            {
                "path": "examples/plan_template.md",
                "content": """# Task: [Title]

## Objective
[One-sentence description of the desired outcome]

## Steps

- [ ] 1. [First step]
  - Details: [What specifically to do]
  - Output: [What this step produces]
- [ ] 2. [Second step]
  - Details: [...]
  - Depends on: Step 1
- [ ] 3. [Third step]
  - Details: [...]

## Status
- Created: [timestamp]
- Current Step: Not started
- Progress: 0/3

## Notes
- [Any assumptions, risks, or open questions]
""",
            },
        ],
    },
    # ─── Skill Creator (mandatory default) ─────────
    {
        "name": "Skill Creator",
        "description": "Create new skills, modify and improve existing skills, and measure skill performance",
        "category": "development",
        "icon": "🛠️",
        "folder_name": "skill-creator",
        "is_default": True,
        "files": [],  # populated at runtime from skill_creator_content
    },
    # ─── Content Research Writer ──────────────────
    {
        "name": "Content Research Writer",
        "description": "Assists in writing high-quality content by conducting research, adding citations, improving hooks, iterating on outlines, and providing real-time section feedback",
        "category": "writing",
        "icon": "✍️",
        "folder_name": "content-research-writer",
        "files": [],  # populated at runtime
    },
    # ─── MCP Tool Installer (mandatory default) ──────────────
    {
        "name": "MCP Tool Installer",
        "description": "Guide users through discovering, configuring, and installing MCP tools directly in chat — no Settings page required",
        "category": "development",
        "icon": "🔌",
        "folder_name": "mcp-installer",
        "is_default": True,
        "files": [],  # populated at runtime from agent_template/skills/MCP_INSTALLER.md
    },
    # ─── OfficeCLI (default) ────────────────────────────────
    {
        "name": "OfficeCLI",
        "description": "Create, read, analyze, and modify Office documents (.docx/.xlsx/.pptx) via the officecli CLI — presentations, reports, spreadsheets, and more",
        "category": "productivity",
        "icon": "📄",
        "folder_name": "officecli",
        "is_default": True,
        "files": [],  # populated at runtime from skill_creator_files/officecli__SKILL.md
    },
]


async def seed_skills():
    """Insert builtin skills if they don't exist."""
    from app.services.skill_creator_content import get_skill_creator_files
    from pathlib import Path as _Path

    _files_dir = _Path(__file__).parent / "skill_creator_files"
    _template_skills_dir = _Path(__file__).parent.parent.parent / "agent_template" / "skills"

    # Populate skill-creator files at runtime
    for s in BUILTIN_SKILLS:
        if s["folder_name"] == "skill-creator" and not s["files"]:
            s["files"] = get_skill_creator_files()
        elif s["folder_name"] == "content-research-writer" and not s["files"]:
            # Load from downloaded file
            crw_file = _files_dir / "content_research_writer__SKILL.md"
            if crw_file.exists():
                s["files"] = [{"path": "SKILL.md", "content": crw_file.read_text(encoding="utf-8")}]
        elif s["folder_name"] == "mcp-installer" and not s["files"]:
            mcp_file = _template_skills_dir / "MCP_INSTALLER.md"
            if mcp_file.exists():
                s["files"] = [{"path": "SKILL.md", "content": mcp_file.read_text(encoding="utf-8")}]
            else:
                logger.warning("[SkillSeeder] MCP_INSTALLER.md not found in agent_template/skills/")
        elif s["folder_name"] == "officecli" and not s["files"]:
            officecli_file = _files_dir / "officecli__SKILL.md"
            if officecli_file.exists():
                s["files"] = [{"path": "SKILL.md", "content": officecli_file.read_text(encoding="utf-8")}]
            else:
                logger.warning("[SkillSeeder] officecli__SKILL.md not found in skill_creator_files/")

    async with async_session() as db:
        for skill_data in BUILTIN_SKILLS:
            result = await db.execute(
                select(Skill).where(Skill.folder_name == skill_data["folder_name"])
            )
            existing = result.scalar_one_or_none()
            is_default = skill_data.get("is_default", False)
            if existing:
                # Update metadata
                existing.name = skill_data["name"]
                existing.description = skill_data["description"]
                existing.category = skill_data["category"]
                existing.icon = skill_data["icon"]
                existing.is_default = is_default
                # Sync files — add missing ones
                from sqlalchemy.orm import selectinload
                res2 = await db.execute(
                    select(Skill).where(Skill.id == existing.id).options(selectinload(Skill.files))
                )
                sk = res2.scalar_one()
                existing_paths = {f.path: f for f in sk.files}
                for f in skill_data["files"]:
                    if f["path"] in existing_paths:
                        # Update content if changed
                        existing_file = existing_paths[f["path"]]
                        if existing_file.content != f["content"]:
                            existing_file.content = f["content"]
                            logger.info(f"[SkillSeeder] Updated {f['path']} in {skill_data['name']}")
                    else:
                        db.add(SkillFile(skill_id=existing.id, path=f["path"], content=f["content"]))
                        logger.info(f"[SkillSeeder] Added file {f['path']} to {skill_data['name']}")
            else:
                skill = Skill(
                    name=skill_data["name"],
                    description=skill_data["description"],
                    category=skill_data["category"],
                    icon=skill_data["icon"],
                    folder_name=skill_data["folder_name"],
                    is_builtin=True,
                    is_default=is_default,
                )
                db.add(skill)
                await db.flush()
                for f in skill_data["files"]:
                    db.add(SkillFile(skill_id=skill.id, path=f["path"], content=f["content"]))
                logger.info(f"[SkillSeeder] Created skill: {skill_data['name']}")
        await db.commit()
        logger.info("[SkillSeeder] Skills seeded")


async def push_default_skills_to_existing_agents():
    """Deploy all is_default skills into the workspace of every existing agent that is missing them.
    
    Called at startup after seed_skills() so existing agents automatically receive new default skills
    like MCP_INSTALLER without requiring manual re-creation.
    """
    from pathlib import Path
    from app.models.agent import Agent
    from app.models.skill import Skill, SkillFile
    from sqlalchemy.orm import selectinload
    from app.services.agent_manager import agent_manager

    async with async_session() as db:
        # Load all is_default skills with their files
        default_skills_r = await db.execute(
            select(Skill).where(Skill.is_default == True).options(selectinload(Skill.files))
        )
        default_skills = default_skills_r.scalars().all()
        if not default_skills:
            return

        # Load all agents
        agents_r = await db.execute(select(Agent))
        agents = agents_r.scalars().all()

        pushed = 0
        updated = 0
        for agent in agents:
            agent_dir = agent_manager._agent_dir(agent.id)
            skills_dir = agent_dir / "skills"
            for skill in default_skills:
                if not skill.files:
                    continue
                skill_folder = skills_dir / skill.folder_name
                skill_folder.mkdir(parents=True, exist_ok=True)
                for sf in skill.files:
                    fp = (skill_folder / sf.path).resolve()
                    fp.parent.mkdir(parents=True, exist_ok=True)
                    if fp.exists():
                        existing_content = fp.read_text(encoding="utf-8")
                        if existing_content == sf.content:
                            continue  # already up-to-date
                        fp.write_text(sf.content, encoding="utf-8")
                        updated += 1
                    else:
                        fp.write_text(sf.content, encoding="utf-8")
                        pushed += 1
                        logger.info(f"[SkillSeeder] Pushed '{skill.name}' to agent {agent.id}")

        if pushed or updated:
            logger.info(f"[SkillSeeder] Pushed {pushed} new + {updated} updated skill files to existing agents")
        else:
            logger.info("[SkillSeeder] All existing agents already have up-to-date default skills")
