[根目录](../CLAUDE.md) > **backend**

# Backend -- Clawith 后端服务

## 模块职责

Clawith 后端是基于 Python 3.12 + FastAPI 构建的企业级 AI 数字员工平台后端，负责：
- REST API 和 WebSocket 实时对话
- Agent（数字员工）生命周期管理
- 多渠道消息网关（飞书、钉钉、企业微信、Discord、Slack、Teams、微信公众号）
- LLM 调用与流式响应
- 多租户隔离、SSO、组织架构同步
- 代码沙箱调度
- 后台定时任务（Trigger Daemon / Scheduler）
- Agent-to-Agent 协作（委派、咨询、通知）
- AgentBay 远程浏览器控制与凭证管理
- Webhook 外部触发集成
- 公司级配置同步（系统提示词、心跳指令）

## 入口与启动

- **应用入口**: `app/main.py` -- FastAPI 应用实例，包含 lifespan 启动流程
- **启动脚本**: `entrypoint.sh` -- Docker 入口点，依次执行：建表 -> Alembic 迁移 -> SEC EDGAR 缓存同步 -> uvicorn 启动
- **配置**: `app/config.py` -- pydantic-settings，从环境变量/`.env` 加载
- **数据库连接**: `app/database.py` -- 异步 SQLAlchemy引擎，连接池 20 + 溢出 10

### 启动流程

1. `create_all` 创建/验证所有数据库表
2. 种子数据初始化（默认租户、内置工具、Agent 模板、技能、默认 Agent）
3. 后台任务启动：Trigger Daemon、飞书 WebSocket、钉钉 Stream、企微 Stream、微信轮询、Discord Gateway
4. SOCKS5 代理启动（用于 Discord API，支持多节点自动切换）
5. uvicorn HTTP 服务监听 8000 端口

## 对外接口

所有 API 前缀为 `/api`，注册在 `app/main.py` 中。主要路由模块：

### 认证与用户

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/auth/*` | `api/auth.py` | 注册、登录、OAuth、密码重置、邮箱验证、多租户切换 |
| `/api/users/*` | `api/users.py` | 用户管理（含渠道账号绑定/解绑/合并） |
| `/api/sso/*` | `api/sso.py` | SSO 登录 |

### Agent 与对话

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/agents/*` | `api/agents.py` | Agent CRUD、归档、启动/停止 |
| `/agents/{id}/relationships/*` | `api/relationships.py` | Agent 关系管理（人-A / A-A 关系） |
| `/agents/{id}/credentials/*` | `api/agent_credentials.py` | Agent 凭证管理（AES-256-CBC 加密存储） |
| `/ws` | `api/websocket.py` | WebSocket 实时对话 |
| `/api/chat-sessions/*` | `api/chat_sessions.py` | 聊天会话管理 |
| `/api/messages/*` | `api/messages.py` | 消息收件箱 |
| `/api/plaza/*` | `api/plaza.py` | Agent 广场（社交动态帖/评论/点赞） |

### 多渠道

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/feishu/*` | `api/feishu.py` | 飞书 OAuth + 消息 |
| `/api/dingtalk/*` | `api/dingtalk.py` | 钉钉集成 |
| `/api/wecom/*` | `api/wecom.py` | 企业微信集成 |
| `/api/wechat/*` | `api/wechat.py` | 微信公众号 |
| `/api/slack/*` | `api/slack.py` | Slack 集成 |
| `/api/discord/*` | `api/discord_bot.py` | Discord Bot |
| `/api/teams/*` | `api/teams.py` | Microsoft Teams |

### 企业与管理

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/enterprise/*` | `api/enterprise.py` | 企业设置 |
| `/api/tenants/*` | `api/tenants.py` | 租户管理（自创建/加入/域名解析） |
| `/api/organization/*` | `api/organization.py` | 组织架构 |
| `/api/admin/*` | `api/admin.py` | 管理后台（平台级） |
| `/api/activity/*` | `api/activity.py` | 活动日志 |

### 工具与技能

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/tools/*` | `api/tools.py` | 工具管理 |
| `/api/skills/*` | `api/skills.py` | 技能管理 |
| `/api/triggers/*` | `api/triggers.py` | 定时触发器 |

### 其他

| 路由 | 文件 | 说明 |
|------|------|------|
| `/api/files/*` | `api/files.py` | 文件管理 |
| `/api/upload/*` | `api/upload.py` | 文件上传 |
| `/api/gateway/*` | `api/gateway.py` | OpenClaw 网关 |
| `/api/notification/*` | `api/notification.py` | 通知服务 |
| `/api/atlassian/*` | `api/atlassian.py` | Atlassian 集成 |
| `/api/pages/*` | `api/pages.py` | 发布页面（含公开路由 `/p/{short_id}`） |
| `/api/agentbay-control/*` | `api/agentbay_control.py` | AgentBay 远程控制（点击/输入/截图/拖拽） |
| `/api/webhooks/t/{token}` | `api/webhooks.py` | Webhook 外部触发（带速率限制） |

### 健康检查

- `GET /api/health` -- 返回 `{status: "ok", version: "..."}`
- `GET /api/version` -- 返回版本号和 commit hash

## 关键依赖与配置

### 核心依赖

- **Web 框架**: FastAPI + uvicorn
- **ORM**: SQLAlchemy 2.0（异步，asyncpg 驱动）
- **数据库迁移**: Alembic
- **缓存**: Redis (hiredis)
- **认证**: python-jose (JWT) + passlib (bcrypt) + AES-256-CBC 加密
- **HTTP 客户端**: httpx（支持 SOCKS5 代理）
- **IM SDK**: lark-oapi (飞书)、dingtalk-stream (钉钉)、wecom-aibot-sdk (企微)、discord.py
- **文档处理**: python-docx、openpyxl、python-pptx、pdfplumber、weasyprint
- **日志**: loguru
- **容器**: docker SDK（用于 Agent 容器管理）
- **加密**: PyNaCl、pycryptodome、cryptography
- **AgentBay**: wuying-agentbay-sdk（远程浏览器控制）
- **拼音/音译**: pypinyin、anyascii（组织架构姓名标准化）
- **MCP**: fastmcp + mcp（可选依赖）

### 配置文件

- `pyproject.toml` -- 项目元数据和依赖
- `alembic.ini` -- Alembic 数据库迁移配置
- `.env` / 环境变量 -- 运行时配置（见根 CLAUDE.md）

## 数据模型

### 核心模型（`app/models/`）

| 模型 | 文件 | 说明 |
|------|------|------|
| Identity | `user.py` | 全局身份（自然人），跨租户 |
| User | `user.py` | 租户内用户（Identity 的租户视图） |
| Tenant | `tenant.py` | 租户（公司），多租户隔离边界 |
| TenantSetting | `tenant_setting.py` | 租户级配置键值（系统提示词、心跳指令等） |
| Agent | `agent.py` | 数字员工实例 |
| AgentCredential | `agent_credential.py` | Agent 加密凭证（用户名/密码/Cookie） |
| LLMModel | `llm.py` | LLM 模型配置 |
| Task | `task.py` | 任务（todo/supervision） |
| ChatSession | `chat_session.py` | 聊天会话 |
| ChatMessage | `audit.py` | 聊天消息（也在 audit 模块） |
| Tool | `tool.py` | 工具定义 |
| Skill | `skill.py` | 技能定义 |
| ChannelConfig | `channel_config.py` | 渠道配置 |
| Trigger | `trigger.py` | 定时触发器 |
| Notification | `notification.py` | 通知 |
| OrgDepartment/OrgMember | `org.py` | 组织架构（部门/成员） |
| IdentityProvider/SSOScanSession | `identity.py` | 身份提供者配置、SSO 扫描会话 |
| PlazaPost/PlazaComment/PlazaLike | `plaza.py` | Agent 广场社交动态 |
| InvitationCode | `invitation_code.py` | 邀请码 |
| ActivityLog | `activity_log.py` | 活动日志 |
| Workspace | `workspace.py` | 工作空间 |
| Participant | `participant.py` | 会话参与者 |
| GatewayMessage | `gateway_message.py` | 网关消息 |
| PublishedPage | `published_page.py` | 发布页面 |
| SystemSettings | `system_settings.py` | 系统级设置 |
| Schedule | `schedule.py` | 定时计划 |

### 数据库迁移

- 迁移目录：`alembic/versions/`（37 个迁移文件）
- 指南：`ALEMBIC_GUIDELINES.md`

## 核心模块（`app/core/`）

| 模块 | 文件 | 说明 |
|------|------|------|
| security | `security.py` | JWT、密码哈希、AES-256-CBC 加密/解密、认证依赖 |
| permissions | `permissions.py` | RBAC 权限检查（`check_agent_access` 统一入口） |
| middleware | `middleware.py` | TraceIdMiddleware（请求追踪 + 全局超时保护 + I/O 信号量） |
| async_utils | `async_utils.py` | `run_sync()` 在线程池中安全执行阻塞 I/O |
| email | `email.py` | 邮件发送 |
| events | `events.py` | Redis 连接管理 |
| logging_config | `logging_config.py` | loguru 配置 + 标准日志拦截 |

## 服务层（`app/services/`）

### 核心服务

| 服务 | 文件 | 说明 |
|------|------|------|
| agent_tools | `agent_tools.py` | Agent 文件系统工具集（读写 workspace/skills/memory） |
| agent_manager | `agent_manager.py` | Agent 生命周期管理 |
| conversation_logger | `conversation_logger.py` | 对话日志记录 |
| model_call/* | `model_call/` | LLM 调用引擎（流式/非流式/多模态） |
| llm_utils | `llm_utils.py` | LLM 通用工具 |
| token_tracker | `token_tracker.py` | Token 用量追踪 |
| quota_guard | `quota_guard.py` | 配额守卫 |
| task_executor | `task_executor.py` | 后台任务执行器（LLM + 工具调用循环） |
| collaboration | `collaboration.py` | Agent-to-Agent 协作（Delegate/Consult/Notify） |
| workspace_paths | `workspace_paths.py` | 工作空间路径解析（防目录遍历） |

### 认证与注册

| 服务 | 文件 | 说明 |
|------|------|------|
| auth_provider | `auth_provider.py` | 通用 OAuth/SSO 认证提供者框架（飞书/钉钉/企微/Teams） |
| auth_registry | `auth_registry.py` | 认证提供者注册表/工厂 |
| registration_service | `registration_service.py` | 用户注册服务（邮箱域名自动检测租户、SSO 注册） |
| email_verification_service | `email_verification_service.py` | 邮箱验证令牌管理（Redis 存储） |
| password_reset_service | `password_reset_service.py` | 密码重置服务 |

### 多渠道服务

| 服务 | 文件 | 说明 |
|------|------|------|
| feishu_service | `feishu_service.py` | 飞书消息处理 |
| feishu_ws | `feishu_ws.py` | 飞书 WebSocket 长连接 |
| dingtalk_service | `dingtalk_service.py` | 钉钉消息处理 |
| dingtalk_stream | `dingtalk_stream.py` | 钉钉 Stream 长连接 |
| wecom_service | `wecom_service.py` | 企微消息处理 |
| wecom_stream | `wecom_stream.py` | 企微 AI Bot WebSocket 长连接 |
| wechat_channel | -- | 微信公众号轮询 |
| wechat_crypto | `wechat_crypto.py` | 微信 iLink CDN 媒体 AES 加密 |
| discord_gateway | `discord_gateway.py` | Discord Bot Gateway |
| channel_session | `channel_session.py` | 渠道会话管理 |

### 组织架构与同步

| 服务 | 文件 | 说明 |
|------|------|------|
| org_sync_adapter | `org_sync_adapter.py` | 通用组织架构同步适配器框架 |
| org_sync_service | `org_sync_service.py` | 组织架构同步服务 |
| enterprise_sync | `enterprise_sync.py` | 企业数据同步 |
| company_config_sync | `company_config_sync.py` | 公司级配置同步（系统提示词 -> Agent 工作空间） |

### 沙箱服务（`services/sandbox/`）

- `config.py` -- 沙箱配置（7 种后端类型）
- `base.py` -- 沙箱基类
- `registry.py` -- 沙箱注册表
- `local/subprocess_backend.py` -- 本地子进程执行
- `local/docker_backend.py` -- Docker 容器执行
- `remote/aio_sandbox_backend.py` -- 远程 AIO 沙箱
- `remote/self_hosted_backend.py` -- 自托管远程沙箱
- `api/e2b_backend.py` -- E2B 沙箱
- `api/judge0_backend.py` -- Judge0 沙箱
- `api/codesandbox_backend.py` -- CodeSandbox 沙箱

### 调度与提醒

| 服务 | 文件 | 说明 |
|------|------|------|
| scheduler | `scheduler.py` | 轻量 asyncio 调度器（cron 表达式，30 秒检查周期） |
| trigger_daemon | `trigger_daemon.py` | 触发器守护进程 |
| supervision_reminder | `supervision_reminder.py` | 监督任务提醒（飞书提醒，按计划发送） |

### 种子/初始化

| 服务 | 文件 | 说明 |
|------|------|------|
| template_seeder | `template_seeder.py` | Agent 模板种子（Project Copilot 等） |
| agent_seeder | `agent_seeder.py` | 审计公司默认 Agent 种子 |
| skill_seeder | `skill_seeder.py` | 技能种子 |
| skill_creator_files/ | -- | 技能创建脚本集 |
| skill_creator_content | `skill_creator_content.py` | 技能创建内容生成 |

### 其他服务

- `word_document_server/` -- Word 文档操作服务（MCP 风格）
- `sec_edgar_server/` -- SEC EDGAR 财务数据服务
- `fetch_server/` -- HTTP 请求代理服务
- `mcp_client.py` -- MCP 协议客户端
- `agentbay_client.py` / `agentbay_live.py` -- AgentBay 远程浏览器控制
- `audit_logger.py` / `activity_logger.py` -- 审计/活动日志
- `notification_service.py` -- 通知服务
- `platform_service.py` -- 平台级管理
- `resource_discovery.py` -- 资源发现（Atlassian Rovo 工具自动导入）
- `tool_artifacts.py` -- 工具产物管理
- `vision_inject.py` -- 视觉注入
- `timezone_utils.py` -- 时区工具

## 测试与质量

- **测试框架**: pytest + pytest-asyncio（`asyncio_mode = "auto"`）
- **Linter**: Ruff（`target-version = "py311"`, `line-length = 120`）
- **测试目录**: `tests/`（6 个测试文件）
- 运行测试：`cd backend && pytest`

## 常见问题 (FAQ)

**Q: 启动时数据库迁移失败怎么办？**
A: 检查 `alembic/versions/` 是否有循环依赖，尝试 `alembic upgrade head` 手动执行。详见 `ALEMBIC_GUIDELINES.md`。

**Q: 如何添加新的 IM 渠道？**
A: 在 `app/api/` 下创建新的路由文件，在 `app/services/` 下创建对应的消息处理服务，并在 `app/main.py` 中注册路由。参考 `auth_provider.py` / `auth_registry.py` 的 SSO 框架。

**Q: Agent 工作空间的文件结构是什么？**
A: 每个 Agent 数据目录包含：`tasks.json`（任务列表）、`soul.md`（人格定义）、`memory.md`（长期记忆）、`skills/`（技能定义）、`workspace/`（工作文件）。`company_config_sync` 会自动同步 `COMPANY_SYSTEM_PROMPT.md` 和 `HEARTBEAT.md`。

**Q: 如何添加新的 SSO 提供者？**
A: 在 `auth_provider.py` 中继承 `BaseAuthProvider` 实现新的提供者类，然后在 `auth_registry.py` 的 `PROVIDER_CLASSES` 中注册。

**Q: 如何添加 Webhook 触发？**
A: 使用 `/api/webhooks/t/{token}` 端点，每个 Trigger 会生成唯一的 webhook token。外部服务 POST 到该 URL 即可触发 Agent。

## 相关文件清单

```
backend/
  app/
    main.py              # 应用入口
    config.py            # 配置（pydantic-settings）
    database.py          # 数据库连接
    api/                 # API 路由（37 个端点模块）
    models/              # SQLAlchemy 模型（26 个表）
    services/            # 业务逻辑服务（90+ 个文件）
    core/                # 中间件、安全、事件、日志、权限、异步工具
    schemas/             # Pydantic 请求/响应 Schema
    scripts/             # 运维脚本
    templates/           # Agent 模板
  alembic/               # 数据库迁移（37 个版本）
  tests/                 # 测试文件
  entrypoint.sh          # Docker 入口脚本
  Dockerfile             # 后端容器镜像
  pyproject.toml         # 项目配置与依赖
  agent_template/        # Agent 默认模板目录
```

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-12T09:56:51 | 增量更新 | 新增 4 个 API 路由（plaza/relationships/webhooks/agent_credentials）、8 个数据模型（identity/plaza/agent_credential 等）、4 个核心模块（security/permissions/middleware/async_utils）、15 个服务（auth_provider/auth_registry/registration_service/company_config_sync/collaboration/task_executor/workspace_paths 等）、迁移文件从 22 增至 37 |
| 2026-05-07T13:40:31 | 初始化 | 首次生成模块文档 |
