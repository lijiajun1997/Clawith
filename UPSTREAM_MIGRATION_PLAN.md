# 上游代码合并迁移方案

> **日期：** 2026-05-06
> **分支：** `audit-firm` ← `dataelement/main`
> **基线版本：** v1.8.3-beta.2 (commit `1b1d8f6`, 2026-04-14)
> **上游最新：** commit `05ac3c9` (2026-05-06)

---

## 1. 背景与目标

### 1.1 现状

`audit-firm` 分支自 2026-04-14 从 main 分叉后独立开发，累计 13 个 commits，主要聚焦：

- SEC EDGAR 金融数据工具集成
- Canvas 文件预览面板
- Dashboard 深度优化
- 移动端聊天适配
- 微信渠道、文件版本控制
- 审计相关系统提示词优化

上游 `dataelement/main` 在同一时期（04-26 ~ 05-06）产生了 **64 个 commits**，涵盖 Workspace 交互、Talent Market、Onboarding、Model Picker、OKR 等大量功能演进。

### 1.2 目标

选择性合并上游有价值的改动，重点关注：

- **Workspace 和 Agent 对话交互** — 上游做了大量 UX 打磨
- **Model Picker 改进** — 默认模型追踪、下拉定位优化
- **MCP 修复** — Smithery 兼容性
- **独立新模块** — document_conversion 等

**排除范围：**

- OKR 系统（明确不需要）
- Talent Market / 模板市场（暂不需要，DB 依赖重）
- Onboarding 仪式（与 Talent Market 强耦合）

### 1.3 差异概览

| 指标 | 数值 |
|------|------|
| 上游新 commits (04-26 起) | 64 |
| 双方同时修改的文件 | 137 |
| 总差异 | 348 files, +45,865 / -37,554 |
| `agent_tools.py` 差异 | +3,715 / -2,172 |
| `AgentDetail.tsx` 差异 | +4,471 / -3,000+ |
| `index.css` 差异 | +5,981 / -5,000+ |

---

## 2. 上游 Commits 分类详览

### 2.1 Tier 1 — Workspace / Agent 对话交互（重点关注）

| Commit | 日期 | 描述 | Files | +/- |
|--------|------|------|-------|-----|
| `24072d7` | 05-02 | Improve agent workspace and chat UX | 61 | +7,264 / -1,611 |
| `1b3672b` | 04-29 | polish agent chat workspace interactions | 4 | +989 / -356 |
| `7396762` | 04-28 | Enhance agent chat and settings UI | 7 | +661 / -147 |
| `99763e4` | 04-30 | Polish agent chat and company logo UI | 8 | +222 / -100 |
| `7d6a083` | 04-29 | Polish agent creation and chat UI | 8 | +189 / -238 |
| `b04648b` | 04-28 | add workspace switcher and company logo settings | 9 | +1,152 / -136 |
| `b3890f8` | 05-04 | refine onboarding and workspace tooling | 22 | +2,210 / -1,209 |
| `05ac3c9` | 05-06 | polish workspace tools and ClawHub imports | 27 | +1,212 / -420 |

**核心变更内容：**

- `AgentDetail.tsx` — 全面重构，新增 workspace 交互面板、工具管理、文件操作
- `WorkspaceOperationPanel.tsx` — 大幅增强，支持文件类型过滤、搜索、Office 提取
- `AgentSidePanel.tsx` — 统一侧边栏交互和样式
- `Chat.tsx` — 对话面板样式完善
- `index.css` — 大量新增 SaaS 风格组件样式（+5000 行）
- `agent_tools.py` — workspace 工具重构，token tracker，vision inject
- `tool_seeder.py` — 工具注册方式重构
- `enterprise_info/.gitkeep` — workspace 企业信息模板目录

**迁移风险：🔴 极高**

这组 commits 之间有强烈依赖关系，尤其是巨型 commit `24072d7` 几乎重写了所有核心文件。单独 cherry-pick 任何一个都会因为缺少前置改动而失败。

---

### 2.2 Tier 1 — Model Picker 改进

| Commit | 日期 | 描述 | Files | +/- |
|--------|------|------|-------|-----|
| `422b16b` | 04-27 | un-clip dropdown, persist picker, propagate tenant default | ~3 | 小 |
| `dd4836f` | 04-27 | always re-sync to agent default | ~2 | 小 |
| `b31f58e` | 04-27 | default badge tracks agent + smart up/down positioning | ~3 | 小 |

**核心变更内容：**

- `ModelSwitcher.tsx` — 修复下拉菜单被裁切、持久化选择、租户默认模型传播
- 依赖 `api.ts` 的 tenant default model API

**迁移风险：🟡 中等** — 前端独立组件，但依赖后端 `add_tenant_default_model` migration

---

### 2.3 Tier 2 — Scope Agent Tools by Tenant

| Commit | 日期 | 描述 | Files | +/- |
|--------|------|------|-------|-----|
| `2910d04` | 05-03 | scope agent tools by tenant | 4 | +140 / -31 |

**核心变更内容：**

- `backend/app/api/tools.py` — 工具查询增加 tenant 过滤
- `backend/app/services/agent_tools.py` — 工具加载逻辑调整
- `backend/tests/test_tool_tenant_scope.py` — 新增测试

**迁移风险：🟡 中等** — 涉及 `agent_tools.py`，与本地改动有冲突

---

### 2.4 Tier 2 — 独立新模块

| Commit | 日期 | 描述 | Files |
|--------|------|------|-------|
| `b3890f8` (部分) | 05-04 | document_conversion 模块 | 5 个新文件 |

新增文件（无冲突）：

- `backend/app/services/document_conversion/__init__.py`
- `backend/app/services/document_conversion/chrome_renderer.py` — Chrome 无头渲染
- `backend/app/services/document_conversion/html_to_pdf.py` — HTML→PDF
- `backend/app/services/document_conversion/html_to_pptx.py` — HTML→PPTX
- `backend/app/services/document_conversion/pptx_renderer.py` — PPTX 渲染器

**迁移风险：🟢 低** — 全新文件，可独立引入

---

### 2.5 Tier 2 — MCP / Smithery 修复

| Commit | 日期 | 描述 |
|--------|------|------|
| `48e7f9f` | 04-27 | live tools/list overrides Smithery stale schema + bare-name lookup |
| `d51df6d` | 04-27 | add Accept header to Smithery Connect tool calls |

**迁移风险：🟢 低** — 独立的 MCP 兼容性修复

---

### 2.6 Tier 2 — Channel 用户身份修复

| Commit | 日期 | 描述 | Files | +/- |
|--------|------|------|-------|-----|
| `7eb30d2` | 04-30 | Fix channel user identity reuse and outbound routing | ~5 | 中等 |

**迁移风险：🟡 中等** — 涉及 channel routing 逻辑

---

### 2.7 Tier 3 — 不合并（排除）

| 分类 | Commits | 原因 |
|------|---------|------|
| OKR 系统 | `9e2d8a8`, `c0c3868`, `f235517`, `00c7d11` | 明确不需要 |
| Talent Market | `9cd8bde`, `3abd4a1`, `f8b5ee3`, `914458f`, `9b1c4d1`, `1ab1d36` 等 ~12 个 | 新功能模块，DB 依赖重，暂不需要 |
| Onboarding 仪式 | `08c3aec`, `4b31d97`, `dd146cc`, `55aaff6` | 与 Talent Market 强耦合 |
| Templates | `9da9fe3`, `221635c`, `bbd71f3`, `83b3f0a`, `845238b` | 依赖 Talent Market |
| CI/CD | `.github/drone.yml` 等 | 部署环境不同 |
| Version bump | `2773505`, `3242149`, `9ba1f46` 等 | 版本管理独立 |

---

## 3. 迁移方案对比

### 3.1 方案 A — Cherry-pick + 手动移植（推荐）

**流程：**

```
Step 1: 引入无冲突新模块
        ├── cherry-pick document_conversion/ 相关文件
        ├── cherry-pick MCP 修复 (48e7f9f, d51df6d)
        └── 验证：import 无报错

Step 2: 移植前端独立组件修复
        ├── cherry-pick Model Picker 修复 (422b16b → dd4836f → b31f58e)
        ├── 可能需要手动适配 api.ts schema 变更
        └── 验证：ModelSwitcher 功能正常

Step 3: 移植 Workspace/Agent 交互（核心工作）
        ├── 不直接 cherry-pick，改为「对比 + 手动合并」
        ├── git diff dataelement/main -- frontend/src/pages/AgentDetail.tsx
        ├── 参考 24072d7 的最终状态，选择性移植：
        │   ├── workspace 文件操作面板交互逻辑
        │   ├── agent 侧边栏交互优化
        │   ├── 对话面板样式改进
        │   └── index.css 中的新组件样式
        └── 验证：UI 交互正常，无回归

Step 4: 移植 agent_tools.py tenant scope
        ├── 参考 2910d04 的改动逻辑
        ├── 在本地 agent_tools.py 上手动加入 tenant 过滤
        └── 验证：工具列表按租户隔离

Step 5: 全量回归测试
        ├── SEC EDGAR 工具功能正常
        ├── Canvas 文件预览正常
        ├── Dashboard 图表正常
        ├── 微信/飞书渠道正常
        └── 移动端适配正常
```

**优势：** 精确控制，不会引入不需要的代码
**劣势：** 工作量大（预计 3-5 天），特别是 Step 3
**适用场景：** 需要保持 audit-firm 分支独立性

---

### 3.2 方案 B — 基于上游重建分支

**流程：**

```
Step 1: 创建新分支
        git checkout -b audit-firm-v2 dataelement/main

Step 2: 逐一 cherry-pick audit-firm 独有功能
        ├── SEC EDGAR 工具集成 (83b023c, 43894fb)
        ├── find_files 性能优化 (cf00b05)
        ├── fetch 网页抓取 (f844125)
        ├── Word/Excel 工具 (fb71622)
        ├── Canvas 面板 (6fecf2c, 1613fd3, 5e68f6e, 51f39a7 等)
        ├── Dashboard 优化 (2351279, 8efd7a8)
        ├── 审计系统提示词 (a42dc18)
        ├── 代码执行环境增强 (5a50cca)
        └── 其他 bug fixes

Step 3: 解决每个 cherry-pick 的冲突
Step 4: 全量回归测试
```

**优势：** 从干净的起点开始，不会有历史包袱
**劣势：** audit-firm 的 13 个 commits 需要逐一适配新版 API，且上游已大幅修改了 agent_tools / AgentDetail，每个 cherry-pick 都可能有冲突
**适用场景：** 如果决定全面拥抱上游架构

---

### 3.3 方案 C — 全量 Merge + 手动解决冲突

**流程：**

```
Step 1: git merge dataelement/main --no-commit
Step 2: 逐文件解决 137 个冲突文件
Step 3: 重点处理三大文件：
        ├── agent_tools.py — 需要完整重做合并
        ├── AgentDetail.tsx — 需要完整重做合并
        └── index.css — 需要完整重做合并
Step 4: 删除不需要的 OKR / Talent Market 相关代码
Step 5: 修复 alembic migration heads（上游新增 ~20 个 migration）
Step 6: 全量回归测试
```

**优势：** 一次性同步所有上游改动
**劣势：** 冲突解决工作量最大，容易引入 bug，且会带入不需要的功能
**适用场景：** 不推荐，除非有充足测试时间

---

### 3.4 方案选择建议

| 维度 | 方案 A | 方案 B | 方案 C |
|------|--------|--------|--------|
| 工作量 | 3-5 天 | 4-6 天 | 5-8 天 |
| 风险可控性 | ✅ 高 | ✅ 中 | ❌ 低 |
| 代码干净度 | 🟡 中 | ✅ 高 | ❌ 低 |
| 上游同步完整度 | 🟡 部分 | ✅ 完整 | ✅ 完整 |
| 对现有功能的影响 | ✅ 小 | 🟡 中 | ❌ 大 |

**最终推荐：方案 A** — 精确控制迁移范围，保护 audit-firm 已有功能的稳定性。

---

## 4. 详细执行计划（方案 A）

### Phase 1：无风险模块引入（预计 0.5 天）

| 步骤 | 操作 | 验证 |
|------|------|------|
| 1.1 | 从 `b3890f8` 提取 `document_conversion/` 5个新文件 | `python -c "from app.services.document_conversion import ..."` 无报错 |
| 1.2 | cherry-pick `48e7f9f` MCP 修复 | MCP 工具调用正常 |
| 1.3 | cherry-pick `d51df6d` Smithery Accept header | Smithery 工具调用正常 |

### Phase 2：前端独立组件修复（预计 0.5 天）

| 步骤 | 操作 | 验证 |
|------|------|------|
| 2.1 | cherry-pick `422b16b` ModelSwitcher un-clip | 下拉菜单不被裁切 |
| 2.2 | cherry-pick `dd4836f` re-sync default | 默认模型正确同步 |
| 2.3 | cherry-pick `b31f58e` badge positioning | badge 定位正确 |
| 2.4 | 检查 `api.ts` 是否需要 tenant default model API | 如需要，从 `3abd4a1` 提取 |

### Phase 3：Workspace / Agent 交互移植（预计 2-3 天，核心工作）

#### 3.1 信息收集

```bash
# 查看上游 AgentDetail.tsx 最终状态的完整内容
git show dataelement/main:frontend/src/pages/AgentDetail.tsx > /tmp/upstream_AgentDetail.tsx

# 对比差异，识别新增功能点
git diff audit-firm dataelement/main -- frontend/src/pages/AgentDetail.tsx

# 对比 WorkspaceOperationPanel
git diff audit-firm dataelement/main -- frontend/src/components/WorkspaceOperationPanel.tsx

# 对比 AgentSidePanel
git diff audit-firm dataelement/main -- frontend/src/components/AgentSidePanel.tsx

# 对比 Chat.tsx
git diff audit-firm dataelement/main -- frontend/src/pages/Chat.tsx

# 提取 index.css 新增的样式块
git diff audit-firm dataelement/main -- frontend/src/index.css
```

#### 3.2 逐文件移植策略

**`AgentDetail.tsx`：**
- 不整体替换，采用「增量移植」策略
- 识别上游新增的交互逻辑（workspace switcher、文件操作按钮、工具管理面板）
- 逐个功能点手动合入，保留 audit-firm 的 SEC EDGAR / Canvas 等功能
- 注意：上游此文件有 1769 行新增，需要仔细甄别哪些与审计场景相关

**`WorkspaceOperationPanel.tsx`：**
- 上游新增了文件类型过滤、搜索、Office 文件提取优化
- 这些功能对审计场景有价值，建议完整移植
- 需要同步检查 `api/files.py` 的后端支持

**`AgentSidePanel.tsx`：**
- 上游优化了侧边栏交互和标签本地化
- 与本地改动有部分重叠，需要对比后选择性合并

**`index.css`：**
- 上游新增了大量 SaaS 风格组件样式（约 5000 行）
- 建议按组件粒度移植，避免一次性引入所有样式
- 优先移植：AgentDetail 相关面板样式、Workspace 操作面板样式

**`Chat.tsx`：**
- 上游改动较小（+65/-23），主要是样式优化
- 可以直接 cherry-pick 或手动合并

#### 3.3 后端适配

**`agent_tools.py`（最大风险点）：**
- 上游重构了 workspace 工具（+2019/-xxx 行）
- 建议：不直接合并，而是参考上游最终状态，在本地 agent_tools.py 中手动添加需要的新工具
- 关键新增工具：document_conversion 相关工具、workspace 协作增强

**`tool_seeder.py`：**
- 上游重构了工具注册方式
- 需要确保新引入的 document_conversion 工具被正确注册

**`api/files.py`：**
- 上游修改了文件 API（+65/-xxx），支持 workspace 新功能
- 需要对比后选择性合并

### Phase 4：Tenant Scope 适配（预计 0.5 天）

| 步骤 | 操作 | 验证 |
|------|------|------|
| 4.1 | 参考 `2910d04` 在 `tools.py` 中添加 tenant 过滤 | 工具列表按租户隔离 |
| 4.2 | 在 `agent_tools.py` 中适配 tenant scope | agent 工具加载正确 |
| 4.3 | cherry-pick `test_tool_tenant_scope.py` 测试 | 测试通过 |

### Phase 5：回归测试（预计 1 天）

| 测试项 | 验证内容 |
|--------|---------|
| SEC EDGAR | ticker 查询、财务报表获取、缓存机制 |
| Canvas 面板 | 文件预览、MD 编辑、拖拽宽度 |
| Dashboard | 图表数据源、对话统计、Token 分布 |
| 移动端 | 聊天页适配、header 简化、文件面板隐藏 |
| 渠道 | 微信/飞书消息收发正常 |
| Workspace | 文件操作、搜索、过滤功能正常 |
| ModelSwitcher | 模型选择、默认追踪、下拉定位 |
| agent_tools | 所有工具正常加载和执行 |

---

## 5. 风险与缓解措施

### 5.1 高风险项

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `agent_tools.py` 合并冲突 | 工具加载失败、功能缺失 | 不直接合并，采用参考 + 手动移植策略 |
| `AgentDetail.tsx` 合并冲突 | 页面渲染异常 | 增量移植，每次只合并一个功能点 |
| `index.css` 样式冲突 | UI 布局错乱 | 按组件粒度移植，每次移植后截图对比 |
| alembic migration 冲突 | 数据库迁移失败 | 不引入上游 migration，只引入代码层面的改动 |

### 5.2 回滚方案

每个 Phase 完成后创建 checkpoint commit，出问题时可快速回退：

```bash
# Phase 1 完成后
git add -A && git commit -m "chore: Phase 1 - 无风险模块引入完成"

# Phase 2 完成后
git add -A && git commit -m "chore: Phase 2 - Model Picker 修复完成"

# Phase 3 每个子步骤完成后
git add -A && git commit -m "chore: Phase 3.x - [具体功能点] 移植完成"
```

---

## 6. 上游 Commits 完整清单（04-26 ~ 05-06）

### 按日期排列

**2026-05-06**
- `05ac3c9` feat: polish workspace tools and ClawHub imports

**2026-05-04**
- `580e3a1` Merge remote-tracking branch 'origin/main'
- `b3890f8` feat: refine onboarding and workspace tooling

**2026-05-03**
- `2910d04` fix: scope agent tools by tenant

**2026-05-02**
- `49b3063` fix(agentbay): use primary category config
- `9fa99f0` fix(plaza): restore visible agent posts
- `2773505` chore: release v1.9.2
- `fdea3fa` Merge release into main
- `24072d7` Improve agent workspace and chat UX

**2026-04-30**
- `9922da1` Merge pull request #511 (version 1.9.1)
- `3242149` chore: bump version to 1.9.1
- `9ba1f46` docs: add v1.9.1 release notes
- `fab875b` Release: merge release branch
- `1e4a39b` update
- `213360e` Merge origin/main into release
- `92c6524` Merge pull request #509
- `7eb30d2` Fix channel user identity reuse and outbound routing
- `99763e4` Polish agent chat and company logo UI
- `461cfa9` Merge PR 503 ux optimization

**2026-04-29**
- `1b3672b` feat(ui): polish agent chat workspace interactions
- `26ab3af` Enhance webpage tools and company region picker
- `7d6a083` Polish agent creation and chat UI

**2026-04-28**
- `7396762` Enhance agent chat and settings UI
- `8e019ef` Merge remote-tracking branch 'origin/pr-497'
- `b04648b` feat(ui): add workspace switcher and company logo settings
- `66d5b22` fix(db): merge only remaining pr494 heads
- `d22d654` docs: update system email configuration guide
- `2d89981` fix(db): decouple credential migration branch
- `19f4ca1` fix(db): stabilize release migration graph
- `d881f35` fix(db): merge alembic heads after pr494
- `0219c5e` fix(frontend): restore dialog hook
- `877c9cd` merge: integrate PR #494 agent market

**2026-04-27**
- `b31f58e` fix(model-picker): default badge positioning
- `dd4836f` fix(model-picker): re-sync to agent default
- `422b16b` fix(model-picker): un-clip dropdown, persist picker
- `dd146cc` perf(onboarding): skip tool list on greeting turn
- `55aaff6` fix(onboarding): lock on first chunk
- `48e7f9f` fix(mcp): live tools/list overrides Smithery
- `d51df6d` fix(mcp): add Accept header to Smithery
- `83b3f0a` feat(templates): auto-install template MCP servers
- `845238b` fix(agents): merge template.default_skills
- `914458f` fix(talent-market): localize agent on hire
- `f8b5ee3` feat(talent-market): search box + zh translations
- `221635c` feat(templates): 10 trading agent templates
- `bbd71f3` feat(skills): market-data + financial-calendar skills
- `9b1c4d1` fix(talent-market): cleaner tab style
- `1ab1d36` feat(templates): polish bootstrap intros
- `1c0bff4` fix(plaza): block private agents
- `9e2d8a8` OKR system, Workspace panel, multi-channel (#492)
- `c0c3868` fix(okr): exclude private agents from sync
- `00c7d11` fix(admin): correct churn warning token totals
- `f235517` fix(relationships): let org admins manage okr

**2026-04-26**
- `4883fba` patch alembic (#482)
- `f5b3b7b` Release (#481)
- `baca673` Release (#480)
- `6f07872` release: OKR系统、Workspace面板、多渠道支持 (#479)

---

## 7. 总结

| 项目 | 内容 |
|------|------|
| **推荐方案** | 方案 A — Cherry-pick + 手动移植 |
| **预计工期** | 4-5 天（含回归测试） |
| **最大风险** | `agent_tools.py` 和 `AgentDetail.tsx` 的合并（采用参考 + 增量移植规避） |
| **合并范围** | Workspace/Agent 交互、Model Picker、MCP 修复、document_conversion 模块 |
| **排除范围** | OKR、Talent Market、Templates、Onboarding 仪式、CI/CD |
| **核心原则** | 每次只引入一个功能点，引入后立即验证，出错可快速回退 |
