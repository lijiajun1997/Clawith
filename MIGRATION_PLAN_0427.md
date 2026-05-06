# 审计版迁移实施方案

> **目标**：基于上游 `dataelement/main` 最新代码（含 PR #479）建立 `audit-firm-0427` 分支，
> 将自研定制功能有序迁移，确保品牌信息、定制工具、UI 优化完整保留，
> 同时获得上游全部新功能。
>
> **背景说明**：我们的二开基于 PR #479 **之前**的上游版本。OKR、多渠道、Workspace 面板等
> 功能在我们 fork 时还不存在，因此不存在"主动删除"——这次合并是**首次获得**这些功能。
>
> **日期**：2026-04-27
> **基线**：`dataelement/main` @ `6f07872`

---

## 一、现状总览

### 1.1 当前分支 `audit-firm`

| 指标 | 数值 |
|------|------|
| 提交数 | 37 |
| 变更文件 | 107 |
| 新增行数 | 25,323 |
| 删除行数 | 1,753 |
| 未提交修改 | AgentDetail.tsx（Mobile 响应式） |

### 1.2 上游 `dataelement/main`（PR #479 合并后）

| 指标 | 数值 |
|------|------|
| PR #479 提交数 | 295 |
| 变更文件 | 111 |
| 新增行数 | ~21,000 |

### 1.3 合并策略

**直接 git merge 不可行** — 两个仓库没有共同祖先（unrelated histories），
111 个文件全部 add/add 冲突。采用 **「上游重建 + 功能迁移」** 策略。

---

## 二、自研功能清单 & 迁移分类

### 分类标识
- **[独有]** 上游完全没有，直接复制
- **[增强]** 上游有基础版，我们做了深度定制
- **[重叠]** 两边有不同实现，需要择优/合并
- **[上游]** 来自上游的新功能，直接保留

---

### 2.1 品牌与 UI 定制 [增强]

| # | 改动 | 文件 | 迁移策略 |
|---|------|------|----------|
| 1 | 登录页品牌信息 | `Login.tsx` | 在上游基础上恢复品牌文字 "Based on open-source project Clawith" |
| 2 | 全局样式定制 | `index.css` | 在上游 CSS 基础上叠加我们的定制部分（变量覆盖、颜色主题） |
| 3 | 聊天增强样式 | `chat-enhanced.css` | 直接复制（上游无此文件） |
| 4 | Tailwind 配置 | `tailwind.config.cjs`, `postcss.config.cjs` | 直接复制 |
| 5 | UI 工具库 | `ui/button.tsx`, `lib/utils.ts` | 直接复制 |
| 6 | Mobile 响应式 | `useIsMobile.ts`, `AgentDetail.tsx` 移动端适配 | 在上游 AgentDetail 基础上重新实现 mobile 判断和样式适配 |
| 7 | 二维码图片 | `assets/QR_Code.png` | 直接复制 |

### 2.2 后端定制工具 [独有]

| # | 工具/模块 | 文件 | 行数 | 说明 | 迁移策略 |
|---|-----------|------|------|------|----------|
| 1 | **SEC EDGAR 工具** | `sec_edgar_server/*` | ~1,700 | 完整的 SEC 财务数据查询工具集 | 直接复制整个目录 |
| 2 | **公司提示词同步** | `company_config_sync.py` | 175 | 公司级系统提示词+心跳指令同步到所有 Agent | 直接复制 + 注册到 main.py |
| 3 | **对话日志服务** | `conversation_logger.py` | 195 | 对话日志记录 | 直接复制 |
| 4 | **工具产物持久化** | `tool_artifacts.py` | ~80 | 自动保存工具结果到 tool_artifacts/ | 直接复制 |
| 5 | **下载文件工具** | `agent_tools.py` 中 `_download_file` | ~80 | 通过 URL 下载文件到 workspace | 合并到上游 agent_tools.py |
| 6 | **call_model 工具** | `agent_tools.py` 中 `_call_model_tool` | ~200 | Agent 内部调用 LLM | 合并到上游 agent_tools.py |
| 7 | **fetch_advanced 工具** | `fetch_server/*` | 236 | 高级网页抓取 | 直接复制 + 注册 |
| 8 | **Word 高级工具** | `word_document_server/*` | ~5,000 | Word 文档高级操作 | 直接复制 + 注册 |
| 9 | **convert_markdown** | `agent_tools.py` + `converters/*` | ~300 | Markdown → Word/Excel 转换 | 保留我们的方案（更灵活），参考上游优化 |
| 10 | **OCR 集成** | `text_extractor.py` 改动 + `agent_tools.py` | ~200 | PDF/图片 OCR 文字识别 | 合并到上游 text_extractor.py |

### 2.3 后端服务改动 [增强/重叠]

| # | 模块 | 文件 | 改动说明 | 迁移策略 |
|---|------|------|----------|----------|
| 1 | **agent_context.py** | `agent_context.py` | 公司系统提示词注入、企业信息注入 | 在上游基础上添加公司提示词注入逻辑 |
| 2 | **agent_tools.py** | `agent_tools.py` | +1,686 行（大量定制工具） | 在上游基础上合并我们的定制工具函数 |
| 3 | **heartbeat.py** | `heartbeat.py` | 公司心跳指令集成 | 在上游基础上添加公司配置读取 |
| 4 | **tool_seeder.py** | `tool_seeder.py` | +395 行（定制工具注册） | 在上游基础上添加我们的工具种子数据 |
| 5 | **entrypoint.sh** | `entrypoint.sh` | 数据库初始化+迁移逻辑 | 采用上游版本（更规范的 alembic 迁移） |
| 6 | **Model Call 模块** | `model_call/*` | ~800 行，模块化 LLM 调用重构 | **评估后决定**：上游有 `llm/caller.py`，功能重叠 |
| 7 | **LLM 客户端** | `llm_client.py`, `llm_utils.py` | 统一 LLM 客户端 | **评估后决定**：上游有 `llm/client.py`，功能重叠 |
| 8 | **sandbox 改动** | `sandbox/*` | 安全策略放宽（审计需要 curl/wget/subprocess），共享依赖，大输出保存 | **保留我们的版本** — 审计场景需要更大的代码执行自由度，同时保留上游 bwrap 隔离作为可选项 |
| 9 | **websocket.py** | `websocket.py` | Canvas 文件卡片渲染、call_llm | 在上游基础上合并 |
| 10 | **enterprise.py** | `enterprise.py` | 公司提示词配置 API | 在上游基础上添加 |

### 2.4 前端定制组件 [独有/增强]

| # | 组件 | 文件 | 行数 | 说明 | 迁移策略 |
|---|------|------|------|------|----------|
| 1 | **Canvas 文件面板** | `FileCanvasPanel.tsx` | 594 | ChatGPT Canvas 风格文件预览面板 | 评估与上游 WorkspaceOperationPanel 的关系 |
| 2 | **最近文件面板** | `RecentFilesPanel.tsx` | 439 | 聊天窗口中的最近文件列表 | 直接复制 |
| 3 | **文档查看器** | `DocumentViewer.tsx` | 117 | jit-viewer 文档预览 SDK 集成 | 直接复制 |
| 4 | **FileBrowser 增强** | `FileBrowser.tsx` | 大量改动 | 文件类型过滤、搜索、Office 预览 | 在上游基础上合并增强 |

### 2.5 前端页面改动 [增强]

| # | 页面 | 改动说明 | 迁移策略 |
|---|------|----------|----------|
| 1 | **AgentDetail.tsx** | Canvas 面板集成、Mobile 响应式、聊天面板样式 | 在上游基础上重新实现定制 |
| 2 | **EnterpriseSettings.tsx** | 批量工具管理、公司提示词配置 | 在上游基础上添加 Tab |
| 3 | **Dashboard.tsx** | 多维度图表、活跃度排名、Token 时间序列 | 在上游 Dashboard 基础上叠加增强 |
| 4 | **PlatformDashboard.tsx** | 数据源修正、统计增强 | 在上游基础上合并 |
| 5 | **Plaza.tsx** | 分页加载、图片错误处理 | 上游已有类似改动，评估后采用更优方案 |
| 6 | **Layout.tsx** | 样式调整 | 在上游基础上微调 |

### 2.6 数据库迁移 [独有]

| # | 迁移文件 | 说明 | 迁移策略 |
|---|----------|------|----------|
| 1 | `add_agent_permissions_indexes.py` | Agent 权限表索引优化 | 基于上游迁移链重建 |
| 2 | `add_chat_messages_indexes.py` | 聊天消息表索引优化 | 基于上游迁移链重建 |
| 3 | `add_notification_is_read_index.py` | 通知表索引优化 | 基于上游迁移链重建 |

### 2.7 上游新增功能（fork 后上游新增，直接保留）

> 以下功能在我们二开时上游尚不存在，本次合并首次引入，全部保留。

| # | 功能 | 主要文件 | 说明 | 保留策略 |
|---|------|----------|------|----------|
| 1 | OKR 系统 | `api/okr.py`, `models/okr.py`, `okr_*.py`, `OKR.tsx` | 完整 OKR 管理 | **保留** — 新功能，按需启用 |
| 2 | Workspace 操作面板 | `WorkspaceOperationPanel.tsx`, `workspace_*.py` | 文件预览/修订/锁定 | **保留** — 与我们的 FileCanvasPanel 互补 |
| 3 | 多渠道支持 | `wechat.py`, `whatsapp.py`, `google_workspace.py` | 微信/WhatsApp/Google | **保留** — 按需启用渠道 |
| 4 | A2A 异步通信 | `agent_tools.py` 中的 notify/task_delegate/consult | Agent 间异步消息 | **保留** — 增强多 Agent 协作 |
| 5 | 主平台会话 | `chat_sessions.py`, `chat_session_service.py` | 会话标记+未读角标 | **保留** |
| 6 | 飞书文档搜索 | `feishu_doc_search` 工具 | 飞书文档搜索 | **保留** |
| 7 | 钉钉媒体消息 | `dingtalk_*.py` 增强 | 图片/文件/语音/视频 | **保留** |
| 8 | CI/CD | `.github/drone.yml` | Drone 流水线 | **保留** |
| 9 | CLAUDE.md | 项目 AI 指导文件 | Claude Code 集成 | **保留** — 替换为我们的版本 |
| 10 | 飞书 WS 稳定性修复 | `feishu_ws.py` | 重连+健康监控 | **保留** — 重要 bug fix |
| 11 | 聊天滚动修复 | `AgentDetail.tsx`, `Layout.tsx` | CSS 高度+flex 修复 | **保留** — 在此基础上叠加我们的定制 |
| 12 | N+1 查询优化 | `chat_sessions.py` | 会话列表批量查询 | **保留** — 性能优化 |
| 13 | Fallback 模型 | `websocket.py`, `llm/caller.py` | 主模型失败自动切换 | **保留** — 与我们的 call_model 互补 |
| 14 | bwrap 沙箱加固 | `subprocess_backend.py` | 代码执行安全隔离 | **评估** — 我们放宽了安全策略（审计需要），需决策 |
| 15 | per-message 模型重载 | `websocket.py` | 每条消息重新读取模型配置 | **保留** — 实时切换模型 |

---

## 三、功能重叠对比 & 决策

### 3.1 文件预览面板（共存）

| 维度 | 我们的 Canvas 面板 | 上游 WorkspaceOperationPanel |
|------|-------------------|------------------------------|
| 核心功能 | 聊天内嵌文件预览、MD 编辑、可拖拽宽度 | 独立侧面板、预览锁定、历史版本、HTML/PDF 富预览 |
| 定位 | 聊天中的轻量级文件预览 | 完整的 Workspace 文件管理面板 |
| 代码量 | ~600 行 | ~1,000+ 行 |
| **决策** | **两者共存**。上游面板处理文件管理/修订/锁定，我们的 Canvas 面板处理聊天中的快速文件预览 |

### 3.2 Model Call 模块（保留我们的 + 上游共存）

| 维度 | 我们的 `model_call/` + `llm_client.py` | 上游 `llm/caller.py` |
|------|----------------------------------------|----------------------|
| 架构 | 8 文件模块化 + 2145 行统一客户端 | 单文件 `caller.py` + `client.py` |
| 功能 | 完整的请求处理、流式输出、多模态、错误处理、会话管理、智谱搜索 | 统一 LLM 调用接口、per-message 重载、failover |
| 使用方 | `call_model` 工具、`websocket.py` 内联调用 | `websocket.py`、`heartbeat.py` 等上游模块 |
| **决策** | **两者共存**。上游 `llm/` 供上游模块使用，我们的 `llm_client.py` + `model_call/` 供 `call_model` 工具和定制功能使用。避免全局替换上游的 LLM 调用链 |

### 3.3 send_web_message vs send_platform_message

| 维度 | 我们的 `send_web_message` | 上游 `send_platform_message` |
|------|--------------------------|------------------------------|
| 功能 | Web 平台消息发送 | 平台消息发送 + A2A 异步通信 |
| 命名 | `send_web_message` | `send_platform_message` |
| **决策** | **采用上游命名** `send_platform_message`，因为上游已整合 A2A 异步通信功能 |

### 3.4 格式转换工具

| 维度 | 我们的 `convert_markdown` + `converters/` | 上游 内置转换 |
|------|---------------------------------------------|--------------|
| 方案 | 外部脚本调用（md2docx.py, md2xlsx.py） | 内嵌在 agent_tools.py 中的 _convert_* |
| 支持格式 | MD → DOCX, MD → XLSX | CSV→XLSX, HTML→PDF, HTML→PPTX, MD→DOCX, MD→PDF |
| **决策** | **合并两者**。保留我们的 `converters/` 目录（质量更高），同时采用上游的 HTML→PDF/PPTX 等我们缺少的格式支持 |

### 3.5 Dashboard 优化

| 维度 | 我们的优化 | 上游改动 |
|------|-----------|---------|
| 功能 | 多维度图表、活跃度排名、Token 时间序列、对话统计 | +139 行基础增强 |
| **决策** | **在上游基础上迁移我们的增强**。上游的 Dashboard 已有基础改动，我们在其上叠加 |

---

## 四、实施步骤

### 阶段 0：准备工作

```bash
# 1. 确保上游最新
git fetch dataelement

# 2. 创建新分支
git checkout -b audit-firm-0427 dataelement/main

# 3. 推送到自己的仓库
git push origin audit-firm-0427

# 4. 验证上游代码能正常启动
cd backend && pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# 新开终端
cd frontend && npm install && npm run dev
```

**验证标准**：上游代码能正常启动、登录、创建 Agent、聊天

---

### 阶段 1：品牌信息 & UI 定制（优先级 P0）

> 目标：恢复我们的品牌标识和 UI 风格

#### 步骤 1.1：登录页品牌信息

**文件**：`frontend/src/pages/Login.tsx`

```
- 找到登录表单区域，添加品牌声明文字 "Based on open-source project Clawith"
- 参考旧分支中的具体位置和样式
```

**预计改动**：~5 行

#### 步骤 1.2：全局样式定制

**文件**：`frontend/src/index.css`

```
- 对比我们的 CSS 变量和上游 CSS 变量
- 添加我们的定制颜色/主题变量（不覆盖上游新增的 OKR/Workspace 样式）
- 叠加我们的自定义样式规则
```

**预计改动**：~100 行增量

#### 步骤 1.3：聊天增强样式

**操作**：直接复制文件

```
frontend/src/chat-enhanced.css          # 2,430 行，聊天面板增强样式
frontend/tailwind.config.cjs            # 60 行，Tailwind 配置
frontend/postcss.config.cjs             # 6 行，PostCSS 配置
frontend/src/components/ui/button.tsx   # 56 行，Button 组件
frontend/src/lib/utils.ts               # 6 行，工具函数
frontend/src/hooks/useIsMobile.ts       # 22 行，Mobile 判断 Hook
```

**注意**：需在 `App.tsx` 或 `main.tsx` 中引入 `chat-enhanced.css`

#### 步骤 1.4：二维码图片

```
assets/QR_Code.png → 直接复制
```

---

### 阶段 2：后端定制工具迁移（优先级 P0）

> 目标：迁移所有自研工具，确保 Agent 可使用

#### 步骤 2.1：整目录复制（独有模块）

```
# 从 audit-firm 分支复制到 audit-firm-0427
backend/app/services/sec_edgar_server/     # SEC EDGAR 工具集（~1,700 行）
backend/app/services/fetch_server/         # 高级网页抓取（236 行）
backend/app/services/word_document_server/ # Word 高级操作（~5,000 行）
backend/app/services/model_call/           # LLM 调用模块（~800 行，备用）
backend/converters/                        # Markdown 转换器（~300 行）
backend/app/templates/                     # 系统提示词模板
```

**注意**：需检查依赖包是否在上游 `pyproject.toml` 中

#### 步骤 2.2：单文件复制（独有服务）

```
backend/app/services/company_config_sync.py  # 公司配置同步（175 行）
backend/app/services/conversation_logger.py   # 对话日志（195 行）
backend/app/services/tool_artifacts.py        # 工具产物持久化（~80 行）
backend/app/services/llm_client.py            # 统一 LLM 客户端（备用）
backend/app/services/llm_utils.py             # LLM 工具函数（备用）
```

#### 步骤 2.3：合并到 `agent_tools.py`（核心文件）

这是最复杂的步骤。**上游 `agent_tools.py` 已有大量改动**（OKR 工具、A2A 通信、
格式转换），我们需要在其基础上**逐函数添加**我们的定制工具。

**需要添加的函数**：

| 函数名 | 功能 | 预计行数 |
|--------|------|----------|
| `_download_file()` | URL 下载文件到 workspace | ~80 |
| `_call_model_tool()` | Agent 内部调用 LLM | ~200 |
| `_convert_markdown()` | MD → DOCX/XLSX 转换 | ~60 |
| `word_advanced()` | Word 文档高级操作 | 委托到 word_document_server |
| `excel_advanced()` | Excel 高级操作 | 委托到 word_document_server |
| `fetch_advanced()` | 高级网页抓取 | 委托到 fetch_server |
| `sec_edgar_advanced()` | SEC EDGAR 查询 | 委托到 sec_edgar_server |
| `_call_llm()` | WebSocket 中直接调用 LLM | ~100 |
| `_jina_search()` 增强 | 增强版搜索 | 已有基础版，评估是否需要增强 |
| `_jina_read()` 增强 | 增强版网页读取 | 同上 |
| `_search_zhipu()` | 智谱搜索 | 检查上游是否已有 |
| `_patch_call_model_description()` | 动态修改工具描述 | ~30 |
| `_persist_tool_result_sync()` | 同步保存工具结果 | ~30 |
| `_is_error_result()` | 错误结果判断 | ~10 |
| OCR 相关函数 | `_load_ocr_config`, PDF/图片 OCR | ~100 |
| `_read_file()` 增强 | OCR 集成 | 在上游基础上添加 OCR 逻辑 |

**执行方式**：
1. 先读取上游 `agent_tools.py` 完整内容
2. 逐个函数从旧分支迁移，确保不破坏上游工具
3. 在 `_TOOL_DISPATCH` 中注册新工具
4. 修改 `tool_seeder.py` 注册新工具种子数据

#### 步骤 2.4：合并到 `tool_seeder.py`

在上游基础上添加我们的工具种子数据：

```python
# 需要添加的种子工具
"send_web_message" → 已在上游有 send_platform_message，跳过
"convert_markdown" → 添加（上游无此工具名）
"excel_advanced"   → 添加
"word_advanced"    → 添加
"download_file"    → 添加
"fetch_advanced"   → 添加
"sec_edgar_advanced" → 添加
"call_model"       → 添加（如上游无此工具）
```

#### 步骤 2.5：合并到 `agent_context.py`

在上游基础上添加公司系统提示词注入：

```python
# 在 build_system_prompt 函数中添加
company_system_prompt = _read_file_safe(ws_root / "COMPANY_SYSTEM_PROMPT.md", 20000)
if company_system_prompt and company_system_prompt.strip():
    # 注入公司配置...
```

#### 步骤 2.6：合并到 `heartbeat.py`

在上游基础上添加公司心跳指令读取：

```python
# 从 COMPANY_SYSTEM_PROMPT.md 读取心跳指令
```

#### 步骤 2.7：合并到 `websocket.py`

添加以下定制：
- Canvas 文件卡片渲染逻辑
- `call_llm` 函数（如上游无此函数）
- 工具产物持久化调用

#### 步骤 2.8：合并到 `enterprise.py`

添加公司提示词配置 API 端点。

#### 步骤 2.9：注册服务到 `main.py`

```python
# 在 startup 事件中添加
from app.services.company_config_sync import start_sync_task
# 启动公司配置同步定时任务
```

---

### 阶段 3：前端定制迁移（优先级 P1）

> 目标：迁移 Canvas 面板、文档查看器、Dashboard 增强等

#### 步骤 3.1：复制独有组件

```
frontend/src/components/FileCanvasPanel.tsx    # 594 行
frontend/src/components/RecentFilesPanel.tsx    # 439 行
frontend/src/components/DocumentViewer.tsx      # 117 行
```

#### 步骤 3.2：合并 `AgentDetail.tsx`

这是最复杂的前端文件（~5,000 行）。上游已有大量改动（聊天滚动修复、
图片去重、Tab 路由等），我们在上游基础上添加：

- Canvas 文件面板集成
- Mobile 响应式（使用 useIsMobile Hook）
- 最近文件面板
- 聊天面板样式增强

**执行方式**：
1. 以上游 AgentDetail.tsx 为基础
2. 逐段从旧分支迁移 Canvas/Mobile 相关代码
3. 引入 `chat-enhanced.css`

#### 步骤 3.3：合并 `EnterpriseSettings.tsx`

在上游基础上添加：
- 批量工具管理 Tab
- 公司提示词配置区域

#### 步骤 3.4：合并 `Dashboard.tsx`

在上游 Dashboard 基础上叠加我们的增强：
- 多维度图表
- 活跃度排名
- Token 时间序列
- 对话统计

#### 步骤 3.5：合并其他页面

- `PlatformDashboard.tsx`：数据源修正
- `Plaza.tsx`：评估是否需要（上游已有分页）
- `Layout.tsx`：微调样式
- `FileBrowser.tsx`：合并文件类型过滤和搜索增强

#### 步骤 3.6：合并 `api.ts`

添加我们的 API 接口（公司配置同步、对话日志等）。

#### 步骤 3.7：合并 i18n

在 `en.json` 和 `zh.json` 中添加我们的翻译条目。

---

### 阶段 4：数据库迁移（优先级 P1）

> 目标：在上游迁移链基础上添加我们的性能优化索引

上游已有一套完整的迁移链（含 OKR 表、Workspace 表、多渠道枚举等）。
我们的 3 个索引迁移需要调整 `down_revision` 挂到上游链末尾。

**操作**：
1. 确认上游迁移链的 head（最新 revision）
2. 创建新的迁移文件，`down_revision` 指向上游 head
3. 添加我们的性能优化索引：
   - `agent_permissions` 表索引
   - `chat_messages` 表索引
   - `notifications` 表复合索引

---

### 阶段 5：配置文件（优先级 P2）

#### 步骤 5.1：`setup.sh` / `restart.sh`

对比我们的版本和上游版本，合并有用的改动（如我们的自动化部署配置）。

#### 步骤 5.2：`docker-compose.yml`

合并我们的定制配置（端口映射、环境变量等）。

#### 步骤 5.3：`backend/pyproject.toml`

检查并添加我们的额外依赖：
- `beautifulsoup4`（HTML 解析）
- OCR 相关依赖
- 其他定制工具依赖

#### 步骤 5.4：`frontend/package.json`

添加我们的额外依赖（如 jit-viewer SDK）。

---

### 阶段 6：系统提示词模板（优先级 P2）

```
backend/app/templates/DEFAULT_COMPANY_SYSTEM_PROMPT.md  # 直接复制
```

这是审计版的核心系统提示词，包含专业审计标准、工具使用规范等。

---

## 五、验证清单

### 5.1 启动验证
- [ ] 后端正常启动，无 import 错误
- [ ] 前端正常构建，无 TypeScript 错误
- [ ] 数据库迁移成功执行
- [ ] Alembic head 无多 head 冲突

### 5.2 功能验证
- [ ] 登录页显示品牌信息
- [ ] Agent 聊天正常工作
- [ ] SEC EDGAR 工具可调用
- [ ] Word/Excel 高级工具可调用
- [ ] fetch_advanced 工具可调用
- [ ] download_file 工具可调用
- [ ] convert_markdown 工具可调用
- [ ] OCR 功能正常（PDF/图片文字识别）
- [ ] 公司系统提示词同步正常
- [ ] Canvas 文件面板正常显示
- [ ] Mobile 响应式布局正常
- [ ] Dashboard 增强图表正常
- [ ] OKR 功能正常（上游新增，首次引入）
- [ ] Workspace 操作面板正常（上游新增，首次引入）
- [ ] 多渠道（微信/WhatsApp/Google）配置页面正常（上游新增）
- [ ] A2A 异步通信正常（上游新增）

### 5.3 性能验证
- [ ] Agent 列表加载无卡顿
- [ ] 聊天消息列表流畅滚动
- [ ] 文件操作响应正常

---

## 六、工作量估算

| 阶段 | 预计时间 | 风险等级 |
|------|----------|----------|
| 阶段 0：准备工作 | 30 分钟 | 低 |
| 阶段 1：品牌 & UI | 2 小时 | 低 |
| 阶段 2：后端工具迁移 | 6-8 小时 | **高**（agent_tools.py 合并） |
| 阶段 3：前端定制迁移 | 4-6 小时 | 中（AgentDetail.tsx 合并） |
| 阶段 4：数据库迁移 | 1 小时 | 低 |
| 阶段 5：配置文件 | 1 小时 | 低 |
| 阶段 6：系统提示词 | 15 分钟 | 低 |
| **总计** | **15-18 小时** | |

---

## 七、风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| `agent_tools.py` 合并冲突 | 工具注册失败 | 逐函数迁移，每个工具独立测试 |
| 上游迁移链与新迁移冲突 | 数据库启动失败 | 仔细检查 down_revision 依赖 |
| 前端组件版本不兼容 | 页面白屏 | 分步验证，每步 npm run build |
| Model Call 模块共存 | call_model 工具与上游 LLM 模块冲突 | 保持隔离：上游 llm/ 供上游模块，我们的 llm_client.py 供定制工具 |
| 上游 Review 指出的安全漏洞 | 权限绕过 | 迁移时顺带修复（OKR 权限校验等） |

---

## 八、执行建议

1. **每完成一个阶段，提交一次代码**，便于回滚
2. **优先完成阶段 0-1**，确保基础可运行
3. **阶段 2 是核心难点**，建议单独安排专注时间
4. **阶段 3 的 AgentDetail.tsx 合并**需要仔细对比
5. 迁移完成后，在上游代码基础上做一次全量测试

---

## 九、参考信息

- 上游 PR：https://github.com/dataelement/Clawith/pull/479
- 上游分支基线：`dataelement/main` @ `6f07872`
- 旧分支：`audit-firm` @ `7402604`
- 新分支：`audit-firm-0427`（待创建）
