[根目录](../CLAUDE.md) > **frontend**

# Frontend -- Clawith 前端 SPA

## 模块职责

Clawith 前端是基于 React 19 + TypeScript + Vite 构建的单页应用（SPA），提供：
- 用户认证与多租户切换（含 JWT 自动刷新）
- AI 数字员工（Agent）创建、管理和对话
- 实时 WebSocket 对话（流式输出）
- 多模型切换（LLM 模型选择器）
- 仪表盘与数据分析（Recharts）
- 平台级仪表盘（PlatformDashboard -- Token 用量/活动统计/趋势图）
- 用户管理（渠道账号绑定/解绑/合并）
- Agent 广场（Plaza 社交动态）
- Agent 凭证管理（AgentCredentials -- 加密存储的登录凭证/Cookie）
- AgentBay 远程浏览器控制（TakeControlPanel -- 截图/点击/输入/拖拽）
- OpenClaw 网关设置
- 企业管理后台
- 国际化（中文/英文）
- 深色/浅色主题切换
- 移动端适配

## 入口与启动

- **HTML 入口**: `index.html`
- **应用入口**: `src/main.tsx` -- React DOM 挂载，配置 QueryClientProvider、BrowserRouter、i18n
- **路由定义**: `src/App.tsx` -- 全部路由配置，含 ProtectedRoute 守卫 + NotificationBar 全局通知栏
- **构建工具**: Vite 6（`vite.config.ts`）
- **开发端口**: 3008，API 代理到 localhost:8008

### 启动命令

```bash
npm install
npm run dev    # 开发模式，端口 3008
npm run build  # 生产构建（tsc + vite build）
```

## 对外接口

前端通过 `src/services/api.ts` 统一调用后端 REST API，所有请求前缀为 `/api`。

### 主要 API 封装

- `authApi` -- 认证（登录、注册、忘记密码、SSO、Token 刷新）
- `agentApi` -- Agent CRUD、对话、协作者、模板
- `tenantApi` -- 租户管理（自创建/加入/域名解析）
- `enterpriseApi` -- 企业设置
- `userManagementApi` -- 用户管理（渠道账号绑定/解绑/合并重复用户）
- `adminApi` -- 平台管理（公司 CRUD、平台设置）
- `credentialApi` -- Agent 凭证管理
- `controlApi` -- AgentBay 远程控制（点击/输入/按键/拖拽/截图/锁定/解锁/当前URL）
- `channelApi` -- 渠道配置（飞书/钉钉/企微/微信等 OAuth 二维码）
- `triggerApi` -- 触发器管理
- `scheduleApi` -- 定时计划管理
- `skillApi` -- 技能管理
- `activityApi` -- 活动日志
- `messageApi` -- 消息收件箱
- `fileApi` -- 文件管理
- `uploadFileWithProgress` -- 带进度的文件上传

### 认证流程

1. JWT Token + Refresh Token 存储在 `localStorage`
2. 所有请求通过 `Authorization: Bearer <token>` 头认证
3. 401 响应自动尝试 Refresh Token 刷新，刷新失败才清除 token 并跳转登录页
4. 支持跨域租户切换（URL `?token=` 参数，自动消费并从 URL 中移除）
5. `/reset-password` 和 `/verify-email` 页面的 `?token=` 不被消费为 JWT

## 关键依赖与配置

### 运行时依赖

| 依赖 | 用途 |
|------|------|
| react 19 | UI 框架 |
| react-router-dom 7 | 路由 |
| @tanstack/react-query 5 | 服务端状态管理 |
| zustand 5 | 客户端状态管理 |
| i18next + react-i18next | 国际化 |
| @tabler/icons-react | 图标库 |
| recharts 3 | 图表 |
| tailwind-merge + clsx + class-variance-authority | 样式工具 |
| @radix-ui/react-slot | 无障碍 UI 原语 |
| lucide-react | 图标 |
| qrcode | 二维码生成 |
| jit-viewer | JIT 查看器 |

### 开发依赖

| 依赖 | 用途 |
|------|------|
| vite 6 | 构建工具 |
| typescript 5 | 类型检查 |
| tailwindcss 3 | CSS 框架 |
| postcss + autoprefixer | CSS 处理 |
| @vitejs/plugin-react | React 支持 |

### 配置文件

- `vite.config.ts` -- Vite 配置（端口、代理、别名、版本注入）
- `tsconfig.json` -- TypeScript 配置（严格模式、路径别名）
- `package.json` -- 依赖和脚本

## 数据模型

前端类型定义在 `src/types/index.ts`，主要类型：

| 类型 | 说明 |
|------|------|
| `User` | 用户（含角色、租户、邮箱验证状态） |
| `ChannelAccount` | 渠道账号（含绑定状态、open_id、unionid 等） |
| `Agent` | 数字员工（含 display_status、agent_type、openclaw_last_seen 等） |
| `Task` | 任务（含 supervision 字段） |
| `ChatMessage` | 聊天消息 |
| `TokenResponse` | 认证响应（含 refresh_token、needs_company_setup） |
| `DashboardSummary` | 仪表盘数据（活动统计、趋势、排名、Token 用量、任务摘要） |

## 页面与路由

### 公开页面

| 路由 | 组件 | 说明 |
|------|------|------|
| `/login` | Login | 登录 |
| `/forgot-password` | ForgotPassword | 忘记密码 |
| `/reset-password` | ResetPassword | 重置密码 |
| `/verify-email` | VerifyEmail | 邮箱验证 |
| `/sso/entry` | SSOEntry | SSO 入口 |
| `/setup-company` | CompanySetup | 公司创建 |

### 受保护页面（Layout 内）

| 路由 | 组件 | 说明 |
|------|------|------|
| `/` | -> `/plaza` | 默认跳转 |
| `/dashboard` | Dashboard | 仪表盘 |
| `/plaza` | Plaza | Agent 广场 |
| `/agents/new` | AgentCreate | 创建 Agent |
| `/agents/:id` | AgentDetail | Agent 详情（含对话、凭证、OpenClaw 设置等标签页） |
| `/messages` | Messages | 消息收件箱 |
| `/enterprise` | EnterpriseSettings | 企业设置 |
| `/invitations` | InvitationCodes | 邀请码管理 |
| `/admin/platform-settings` | AdminCompanies | 平台管理 |

### 独立页面（不在路由中，嵌入 AgentDetail 标签页）

| 组件 | 说明 |
|------|------|
| PlatformDashboard | 平台级仪表盘（Token 用量、活动统计、趋势图） |
| UserManagement | 用户管理（配额、渠道账号绑定/解绑/合并） |
| OpenClawSettings | OpenClaw 网关配置 |
| Chat | 对话面板 |

### 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| AgentCredentials | `components/AgentCredentials.tsx` | Agent 凭证管理（加密存储的用户名/密码/Cookie） |
| TakeControlPanel | `components/TakeControlPanel.tsx` | 人工接管浏览器控制面板（截图/点击/输入/拖拽） |
| ChannelConfig | `components/ChannelConfig.tsx` | 渠道配置面板（OAuth 二维码、连接状态） |
| ModelSwitcher | `components/ModelSwitcher.tsx` | LLM 模型切换器 |
| FileBrowser | `components/FileBrowser.tsx` | 文件浏览器 |
| WorkspaceOperationPanel | `components/WorkspaceOperationPanel.tsx` | 工作空间操作面板 |
| AgentSidePanel | `components/AgentSidePanel.tsx` | Agent 侧面板 |
| AgentBayLivePanel | `components/AgentBayLivePanel.tsx` | AgentBay 实时预览 |
| MarkdownRenderer | `components/MarkdownRenderer.tsx` | Markdown 渲染 |
| DocumentViewer | `components/DocumentViewer.tsx` | 文档查看器 |
| RecentFilesPanel | `components/RecentFilesPanel.tsx` | 最近文件面板 |
| FileCanvasPanel | `components/FileCanvasPanel.tsx` | 文件画布面板 |
| ConfirmModal | `components/ConfirmModal.tsx` | 确认对话框 |
| ErrorBoundary | `components/ErrorBoundary.tsx` | 错误边界 |
| LinearCopyButton | `components/LinearCopyButton.tsx` | Linear 风格复制按钮 |
| PromptModal | `components/PromptModal.tsx` | 提示词模态框 |
| ui/button | `components/ui/button.tsx` | 通用按钮组件（CVA + Radix Slot） |

## 状态管理

### Zustand Stores（`src/stores/index.ts`）

- **AuthStore**: 用户认证状态（token、refreshToken、user、login/logout/setUser）
- **AppStore**: 应用 UI 状态（侧边栏折叠、选中 Agent）

### React Query

- 全局配置：retry=1, refetchOnWindowFocus=false
- 用于服务端数据获取和缓存

## 国际化

- 框架：i18next + react-i18next + i18next-browser-languagedetector
- 语言文件：`src/i18n/zh.json`（中文）、`src/i18n/en.json`（英文）
- 支持语言：中文、英文
- 检测优先级：localStorage > navigator

## 样式与主题

- **CSS 框架**: TailwindCSS 3
- **主题**: 深色/浅色模式（`data-theme` 属性 + localStorage 持久化）
- **主题工具**: `src/utils/theme.ts` -- 加载/保存主题色
- **自定义 CSS**: `src/index.css`（全局样式）、`src/chat-enhanced.css`（对话增强样式）
- **通知栏**: 全局 NotificationBar 组件（支持滚动字幕，从系统设置动态加载）
- **工具函数**: `src/lib/utils.ts` -- cn() 样式合并工具

## 测试与质量

- 当前无前端测试文件
- TypeScript 严格模式开启
- ESLint 未在配置中显式发现（可能使用 Vite 内置检查）

## 常见问题 (FAQ)

**Q: 前端如何代理后端 API？**
A: 开发模式下 Vite 配置了代理：`/api` -> `http://localhost:8008`，`/ws` -> `ws://localhost:8008`。

**Q: 如何添加新页面？**
A: 在 `src/pages/` 创建组件，在 `src/App.tsx` 的路由中注册。

**Q: 如何添加新的国际化文案？**
A: 在 `src/i18n/zh.json` 和 `src/i18n/en.json` 中添加对应的键值对。

**Q: JWT Token 刷新机制是如何工作的？**
A: `services/api.ts` 中的 `request()` 函数在收到 401 时自动调用 `tryRefreshToken()`，使用 localStorage 中的 `refresh_token` 刷新 access_token。同一时刻只允许一个刷新请求（互斥锁）。

**Q: 跨域租户切换是如何实现的？**
A: 后端在重定向 URL 中附加 `?token=<jwt>`，前端 `App.tsx` 在初始化时消费该 token（排除 `/reset-password` 和 `/verify-email` 路径），然后从 URL 中移除以防止泄露到浏览器历史。

## 相关文件清单

```
frontend/
  src/
    main.tsx             # 应用挂载入口
    App.tsx              # 路由定义 + NotificationBar
    index.css            # 全局样式
    chat-enhanced.css    # 对话样式
    vite-env.d.ts        # Vite 类型声明
    pages/               # 页面组件（19 个）
    components/          # 通用组件（17 个）
    services/api.ts      # API 调用层（含 JWT 刷新）
    stores/index.ts      # Zustand 状态管理
    types/index.ts       # TypeScript 类型定义
    i18n/                # 国际化资源
    hooks/               # 自定义 Hooks
    utils/               # 工具函数
    lib/utils.ts         # cn() 样式合并
  package.json           # 依赖配置
  vite.config.ts         # Vite 配置
  tsconfig.json          # TypeScript 配置
  Dockerfile             # 前端容器镜像（多阶段：build -> nginx）
  nginx.conf             # Nginx 配置
```

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-12T09:56:51 | 增量更新 | 新增 3 个页面（PlatformDashboard/UserManagement/OpenClawSettings）、8 个组件（AgentCredentials/TakeControlPanel/ChannelConfig/ConfirmModal/ErrorBoundary/LinearCopyButton/PromptModal/ui-button）、新增 API 封装（userManagementApi/credentialApi/controlApi/channelApi/triggerApi）、类型新增 ChannelAccount、AuthStore 新增 refreshToken/setUser、JWT 自动刷新机制、跨域租户切换说明 |
| 2026-05-07T13:40:31 | 初始化 | 首次生成模块文档 |
