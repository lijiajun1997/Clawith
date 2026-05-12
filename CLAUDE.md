# Clawith -- 企业数字员工平台

## 项目愿景

Clawith (Proud Copilot) 是一个企业级 AI 数字员工平台，核心能力包括：
- 创建和管理 AI 数字员工（Agent），每个 Agent 拥有独立人格、知识、技能和工作空间
- 多渠道对话接入：Web、飞书、钉钉、企业微信、Discord、Slack、Microsoft Teams、微信公众号
- 实时 WebSocket 对话，支持流式输出和工具调用
- 多租户（Tenant）隔离，支持 SSO、组织架构同步
- 代码沙箱执行，支持 Python/Bash/Node.js
- Agent-to-Agent 协作（委派、咨询、通知）
- AgentBay 远程浏览器控制（Take Control / CDP 注入）
- Webhook 外部触发集成
- Helm Chart 支持企业级 Kubernetes 部署

技术栈：Python 3.12 / FastAPI / PostgreSQL / Redis / React 19 / TypeScript / Vite / TailwindCSS / Zustand

## 架构总览

系统采用前后端分离 + 独立沙箱微服务架构，通过 Docker Compose 或 Kubernetes 编排部署：

- **backend** -- Python/FastAPI 后端，包含 REST API、WebSocket、后台任务、多渠道网关
- **frontend** -- React/TypeScript SPA，Vite 构建，Nginx 托管
- **sandbox** -- 独立代码执行沙箱微服务（FastAPI），支持多语言运行时
- **helm** -- Kubernetes Helm Chart 部署配置

数据库：PostgreSQL 15（异步 SQLAlchemy + Alembic 迁移）
缓存/消息：Redis 7
容器编排：Docker Compose / Kubernetes (Helm)

## 模块结构图

```mermaid
graph TD
    A["Clawith (根)"] --> B["backend"]
    A --> C["frontend"]
    A --> D["sandbox"]
    A --> E["helm"]

    B --> B1["app/api"]
    B --> B2["app/models"]
    B --> B3["app/services"]
    B --> B4["app/core"]
    B --> B5["alembic"]

    C --> C1["src/pages"]
    C --> C2["src/components"]
    C --> C3["src/services"]
    C --> C4["src/stores"]
    C --> C5["src/i18n"]

    click B "./backend/CLAUDE.md" "查看 backend 模块文档"
    click C "./frontend/CLAUDE.md" "查看 frontend 模块文档"
    click D "./sandbox/CLAUDE.md" "查看 sandbox 模块文档"
    click E "./helm/CLAUDE.md" "查看 helm 模块文档"
```

## 模块索引

| 模块 | 路径 | 语言 | 职责 |
|------|------|------|------|
| backend | `backend/` | Python 3.12 | FastAPI 后端：REST API、WebSocket、多渠道网关、LLM 调用、Agent 管理 |
| frontend | `frontend/` | TypeScript / React 19 | SPA 前端：对话界面、Agent 管理、仪表盘、企业管理 |
| sandbox | `sandbox/` | Python 3.12 | 独立代码执行沙箱微服务，支持 Python/Bash/Node.js |
| helm | `helm/` | YAML | Kubernetes Helm Chart 部署配置 |

## 运行与开发

### 环境要求

- Python >= 3.11（后端推荐 3.12）
- Node.js >= 20（前端）
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose（推荐方式）

### 快速启动（Docker Compose）

```bash
# 一键启动所有服务
docker compose up -d

# 服务端口
# backend:  http://localhost:8000
# frontend: http://localhost:3008
# sandbox:  http://localhost:8888
```

### 本地开发

```bash
# 后端
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev  # 端口 3008，代理 /api -> localhost:8008

# 沙箱
cd sandbox
pip install -r requirements.txt
python -m uvicorn service:app --host 0.0.0.0 --port 8888
```

### 关键环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+asyncpg://clawith:clawith@localhost:5432/clawith` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `SECRET_KEY` | 应用密钥 | `change-me-in-production` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | `change-me-jwt-secret` |
| `AGENT_DATA_DIR` | Agent 数据目录 | 容器内 `/data/agents`，本地 `~/.clawith/data/agents` |
| `SANDBOX_TYPE` | 沙箱类型 | `pool_sandbox` |
| `SANDBOX_API_URL` | 沙箱服务地址 | `http://sandbox:8888` |
| `PUBLIC_BASE_URL` | 公网 URL（OAuth/邮件链接） | 空 |
| `SS_CONFIG_FILE` | SOCKS5 代理节点配置 | `/data/ss-nodes.json` |

## 测试策略

### 后端测试

- 框架：pytest + pytest-asyncio（asyncio_mode = "auto"）
- 测试目录：`backend/tests/`
- 现有测试：
  - `test_agent_delete_api.py` -- Agent 删除 API
  - `test_feishu_service_api.py` -- 飞书服务 API
  - `test_password_reset_and_notifications.py` -- 密码重置与通知
  - `test_skills_api.py` -- 技能 API
  - `test_a2a_msg_type.py` -- Agent-to-Agent 消息类型
  - `test_chat_sessions_api.py` -- 聊天会话 API

### 沙箱测试

- `sandbox/test_sandbox.py` -- 沙箱服务基本功能测试

### 前端测试

- 当前无专门的前端测试目录

## 编码规范

### 后端（Python）

- Linter: Ruff（target Python 3.11, line-length 120）
- 配置在 `pyproject.toml` 的 `[tool.ruff]` 节
- 异步优先：所有 DB 操作使用 async SQLAlchemy
- 阻塞 I/O 必须通过 `core/async_utils.run_sync()` 在线程池中执行
- 日志：loguru，带 trace-id 追踪（通过 `core/middleware.TraceIdMiddleware`）
- 权限检查：`core/permissions.check_agent_access()` RBAC 统一入口

### 前端（TypeScript/React）

- 严格模式启用（`tsconfig.json` 中 `"strict": true`）
- 路径别名：`@/*` -> `./src/*`
- 状态管理：Zustand（AuthStore + AppStore）
- 样式：TailwindCSS + CSS 变量主题
- 国际化：i18next（中文/英文）
- API 层：统一通过 `services/api.ts` 的 `request()` 函数，自动处理 JWT 刷新和 401 重定向

### 数据库迁移

- 工具：Alembic
- 目录：`backend/alembic/versions/`（37 个迁移文件）
- 指南：`backend/ALEMBIC_GUIDELINES.md`
- 入口点脚本自动执行 `create_all` + `alembic upgrade head`

## AI 使用指引

- 本项目已有 `AGENTS.md` 指引文件，AI 开发时应先阅读
- 详细设计规则在 `.agents/rules/` 目录下
- 架构规范参考 `.agents/workflows/read_architecture.md`
- Agent 工作空间使用固定路径结构：`tasks.json`, `soul.md`, `memory.md`, `skills/`, `workspace/`

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-12T09:56:51 | 增量更新 | 补充新增 API（plaza/relationships/webhooks/agent_credentials）、新增模型（identity/plaza/agent_credential 等 8 个）、新增核心模块（security/permissions/middleware/async_utils）、新增 15 个服务、前端新增 3 页面 8 组件、37 个迁移文件 |
| 2026-05-07T13:40:31 | 初始化 | 全仓扫描，生成根级与模块级文档 |
