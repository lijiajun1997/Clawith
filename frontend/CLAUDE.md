[根目录](../CLAUDE.md) > **frontend**

# Frontend -- Clawith 前端 SPA

## 模块职责

Clawith 前端是基于 React 19 + TypeScript + Vite 构建的单页应用（SPA），提供：
- 用户认证与多租户切换
- AI 数字员工（Agent）创建、管理和对话
- 实时 WebSocket 对话（流式输出）
- 多模型切换（LLM 模型选择器）
- 仪表盘与数据分析（Recharts）
- 企业管理后台
- 国际化（中文/英文）
- 深色/浅色主题切换
- 移动端适配

## 入口与启动

- **HTML 入口**: `index.html`
- **应用入口**: `src/main.tsx` -- React DOM 挂载，配置 QueryClientProvider、BrowserRouter、i18n
- **路由定义**: `src/App.tsx` -- 全部路由配置，含 ProtectedRoute 守卫
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

- `authApi` -- 认证（登录、注册、忘记密码、SSO）
- `agentApi` -- Agent CRUD、对话
- `tenantApi` -- 租户管理
- `enterpriseApi` -- 企业设置
- `uploadFileWithProgress` -- 带进度的文件上传

### 认证流程

1. JWT Token 存储在 `localStorage`
2. 所有请求通过 `Authorization: Bearer <token>` 头认证
3. 401 响应自动清除 token 并跳转登录页
4. 支持跨域租户切换（URL ?token= 参数）

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
| recharts | 图表 |
| tailwind-merge + clsx | 样式工具 |
| @radix-ui/react-slot | 无障碍 UI 原语 |
| lucide-react | 图标 |
| qrcode | 二维码生成 |

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
- `tailwind.config.js` -- TailwindCSS 配置（推测存在）
- `package.json` -- 依赖和脚本

## 数据模型

前端类型定义在 `src/types/index.ts`，主要类型：

| 类型 | 说明 |
|------|------|
| `User` | 用户（含角色、租户、邮箱验证状态） |
| `Agent` | 数字员工（含状态、配额、心跳配置） |
| `Task` | 任务 |
| `ChatMessage` | 聊天消息 |
| `TokenResponse` | 认证响应 |
| `DashboardSummary` | 仪表盘数据（活动统计、趋势、排名） |

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
| `/agents/:id` | AgentDetail | Agent 详情（含对话） |
| `/messages` | Messages | 消息收件箱 |
| `/enterprise` | EnterpriseSettings | 企业设置 |
| `/invitations` | InvitationCodes | 邀请码管理 |
| `/admin/platform-settings` | AdminCompanies | 平台管理 |

### 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| Chat | `pages/Chat.tsx` | 对话面板（嵌入 AgentDetail） |
| Layout | `pages/Layout.tsx` | 主布局（侧边栏、导航） |
| ModelSwitcher | `components/ModelSwitcher.tsx` | LLM 模型切换器 |
| FileBrowser | `components/FileBrowser.tsx` | 文件浏览器 |
| WorkspaceOperationPanel | `components/WorkspaceOperationPanel.tsx` | 工作空间操作面板 |
| AgentSidePanel | `components/AgentSidePanel.tsx` | Agent 侧面板 |
| AgentBayLivePanel | `components/AgentBayLivePanel.tsx` | AgentBay 实时预览 |
| MarkdownRenderer | `components/MarkdownRenderer.tsx` | Markdown 渲染 |
| DocumentViewer | `components/DocumentViewer.tsx` | 文档查看器 |
| RecentFilesPanel | `components/RecentFilesPanel.tsx` | 最近文件面板 |
| FileCanvasPanel | `components/FileCanvasPanel.tsx` | 文件画布面板 |

## 状态管理

### Zustand Stores（`src/stores/index.ts`）

- **AuthStore**: 用户认证状态（token、user、login/logout）
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
- **通知栏**: 全局 NotificationBar 组件（支持滚动字幕）

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

## 相关文件清单

```
frontend/
  src/
    main.tsx             # 应用挂载入口
    App.tsx              # 路由定义
    index.css            # 全局样式
    chat-enhanced.css    # 对话样式
    vite-env.d.ts        # Vite 类型声明
    pages/               # 页面组件（15+ 个）
    components/          # 通用组件
    services/api.ts      # API 调用层
    stores/index.ts      # Zustand 状态管理
    types/index.ts       # TypeScript 类型定义
    i18n/                # 国际化资源
    hooks/               # 自定义 Hooks
    utils/               # 工具函数
    lib/                 # 第三方库封装
  package.json           # 依赖配置
  vite.config.ts         # Vite 配置
  tsconfig.json          # TypeScript 配置
  Dockerfile             # 前端容器镜像（多阶段：build -> nginx）
  nginx.conf             # Nginx 配置
```

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-07T13:40:31 | 初始化 | 首次生成模块文档 |
