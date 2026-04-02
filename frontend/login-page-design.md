# ProudCopilot 登录页设计文档

## 概述

本文档记录了 ProudCopilot 登录页面的设计方案，便于后续按官方版本重构时参考。

---

## 1. 页面布局结构

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        登录页面                                  │
├────────────────────────────┬────────────────────────────────────┤
│                            │                                    │
│      左侧品牌展示区         │         右侧表单区                   │
│      (login-hero)          │      (login-form-panel)            │
│                            │                                    │
│   - 背景装饰层              │    - 语言切换按钮                   │
│   - 图形装饰元素            │    - Logo + 标题                   │
│   - 标题 + 描述             │    - 登录/注册表单                  │
│   - 4个功能卡片             │    - SSO 登录按钮                   │
│                            │    - 切换登录/注册链接               │
│                            │                                    │
└────────────────────────────┴────────────────────────────────────┘
```

### 1.2 响应式设计

- **桌面端**: 左右分栏布局 (左 60% / 右 40%)
- **移动端**: 单栏布局，左侧品牌区隐藏或简化

---

## 2. 左侧品牌展示区 (login-hero)

### 2.1 结构层次

```html
<div class="login-hero">
    <!-- 背景层 -->
    <div class="login-hero-bg" />

    <!-- 装饰层 -->
    <div class="login-hero-decor" />

    <!-- 图形装饰元素 -->
    <div class="login-hero-shapes">
        <!-- 地球图形 -->
        <div class="login-hero-chart login-hero-chart--globe">
            <svg>...</svg>
        </div>

        <!-- 股票图表 -->
        <div class="login-hero-chart login-hero-chart--stock">
            <svg>...</svg>
        </div>

        <!-- 柱状图 -->
        <div class="login-hero-chart login-hero-chart--bar">
            <svg>...</svg>
        </div>

        <!-- 饼图 -->
        <div class="login-hero-chart login-hero-chart--pie">
            <svg>...</svg>
        </div>

        <!-- 趋势线 -->
        <div class="login-hero-chart login-hero-chart--trend">
            <svg>...</svg>
        </div>

        <!-- 装饰圆球 -->
        <div class="login-hero-orb login-hero-orb--1"></div>
        <div class="login-hero-orb login-hero-orb--2"></div>
        <div class="login-hero-orb login-hero-orb--3"></div>

        <!-- 货币符号 -->
        <div class="login-hero-symbol login-hero-symbol--dollar">$</div>
        <div class="login-hero-symbol login-hero-symbol--yen">¥</div>
        <div class="login-hero-symbol login-hero-symbol--euro">€</div>
        <div class="login-hero-symbol login-hero-symbol--pound">£</div>
        <div class="login-hero-symbol login-hero-symbol--dollar2">$</div>
        <div class="login-hero-symbol login-hero-symbol--percent">%</div>
    </div>

    <!-- 网格背景 -->
    <div class="login-hero-grid" />

    <!-- 内容层 -->
    <div class="login-hero-content">
        <!-- 徽章 -->
        <div class="login-hero-badge">
            <span class="login-hero-badge-dot" />
            {t('login.hero.badge')}
        </div>

        <!-- 主标题 -->
        <h1 class="login-hero-title">
            {t('login.hero.title')}<br />
            <span>{t('login.hero.subtitle')}</span>
        </h1>

        <!-- 描述 -->
        <p class="login-hero-desc" dangerouslySetInnerHTML={{ __html: t('login.hero.description') }} />

        <!-- 功能卡片 -->
        <div class="login-hero-features">
            <!-- 4个功能卡片 -->
        </div>
    </div>
</div>
```

### 2.2 功能卡片设计

```tsx
// 使用 Tabler Icons 图标库
import { IconUsers, IconBrain, IconBuilding, IconRocket } from '@tabler/icons-react';

// 卡片数据结构
const features = [
    {
        icon: IconUsers,
        titleKey: 'login.hero.features.multiAgent.title',
        descKey: 'login.hero.features.multiAgent.description',
    },
    {
        icon: IconBrain,
        titleKey: 'login.hero.features.persistentMemory.title',
        descKey: 'login.hero.features.persistentMemory.description',
    },
    {
        icon: IconBuilding,
        titleKey: 'login.hero.features.serviceDelivery.title',
        descKey: 'login.hero.features.serviceDelivery.description',
    },
    {
        icon: IconRocket,
        titleKey: 'login.hero.features.learning.title',
        descKey: 'login.hero.features.learning.description',
    },
];

// 单个卡片渲染
<div className="login-hero-feature">
    <IconComponent size={24} stroke={1.5} className="login-hero-feature-icon" />
    <div>
        <div className="login-hero-feature-title">{t(titleKey)}</div>
        <div className="login-hero-feature-desc">{t(descKey)}</div>
    </div>
</div>
```

### 2.3 CSS 样式要点

```css
/* Hero 区域基础 */
.login-hero {
    flex: 1;
    min-width: 0;
    background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 50%, #2563eb 100%);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px;
    position: relative;
    overflow: hidden;
    color: #fff;
}

/* 功能卡片网格 - 2x2 布局 */
.login-hero-features {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

/* 单个卡片 */
.login-hero-feature {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    gap: 16px;
    padding: 20px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    min-height: 88px; /* 确保等高 */
    transition: all 250ms ease;
}

.login-hero-feature:hover {
    background: rgba(255, 255, 255, 0.07);
    border-color: rgba(255, 255, 255, 0.1);
    transform: translateY(-2px);
}

/* 图标容器 */
.login-hero-feature-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    border-radius: 10px;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    flex-shrink: 0;
}

/* 标题样式 */
.login-hero-feature-title {
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -0.005em;
    margin-bottom: 4px;
}

/* 描述样式 */
.login-hero-feature-desc {
    font-size: 12px;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.5);
}
```

---

## 3. 右侧表单区 (login-form-panel)

### 3.1 布局结构

```html
<div class="login-form-panel">
    <!-- 语言切换 -->
    <div style="position: absolute; top: 16px; right: 16px;">
        <button onClick={toggleLang}>🌐</button>
    </div>

    <!-- 表单容器 -->
    <div class="login-form-wrapper">
        <!-- Logo + 标题 -->
        <div class="login-form-header">
            <div class="login-form-logo">
                <img src="/logo-black.png" />
                ProudCopilot
            </div>
            <h2>{t('auth.login')}</h2>
            <p>{t('auth.subtitleLogin')}</p>
        </div>

        <!-- 错误提示 -->
        {error && <div class="login-error">...</div>}

        <!-- SSO 登录（可选显示） -->
        {tenant?.sso_enabled && <SSOButtons />}

        <!-- 登录表单 -->
        <form onSubmit={handleSubmit}>
            <input type="text" placeholder="邮箱/用户名" />
            <input type="password" placeholder="密码" />
            <button type="submit">登录</button>
        </form>

        <!-- 切换链接 -->
        <div class="login-switch">
            {t('auth.noAccount')} <a onClick={toggleRegister}>注册</a>
        </div>
    </div>
</div>
```

### 3.2 表单字段设计

```tsx
// 登录表单支持用户名/邮箱/手机号
const [form, setForm] = useState({
    login_identifier: '',  // 支持用户名、邮箱或手机号
    password: '',
    tenant_id: '',         // 多租户选择
});

// 输入框
<input
    type="text"  // 注意：使用 text 而非 email，支持多种登录方式
    value={form.login_identifier}
    placeholder={t('auth.emailOrUsernamePlaceholder', '邮箱、用户名或手机号')}
/>

// API 调用
authApi.login({
    login_identifier: form.login_identifier,
    password: form.password,
    tenant_id: form.tenant_id || undefined,
});
```

---

## 4. 多租户登录支持

### 4.1 租户选择弹窗

当用户邮箱对应多个租户时，显示选择弹窗：

```tsx
{tenantSelection && (
    <div class="tenant-selection-modal">
        <h3>{t('auth.selectOrganization')}</h3>
        <p>{t('auth.multiTenantPrompt')}</p>

        {tenantSelection.map(tenant => (
            <button onClick={() => handleTenantSelect(tenant.tenant_id)}>
                {tenant.tenant_name}
            </button>
        ))}

        <button onClick={() => navigate('/setup-company')}>
            {t('auth.createOrJoinOrganization')}
        </button>
    </div>
)}
```

---

## 5. 国际化配置

### 5.1 中文翻译 (zh.json)

```json
{
    "login": {
        "hero": {
            "badge": "企业级 AI 数字员工平台",
            "title": "智能协作",
            "subtitle": "重新定义企业数字化",
            "description": "打造专业的 AI 数字员工团队，<br>为企业提供持续进化的智能服务能力。",
            "features": {
                "multiAgent": {
                    "title": "团队协作",
                    "description": "数字员工智能协同，高效完成复杂任务"
                },
                "serviceDelivery": {
                    "title": "专业交付",
                    "description": "稳定可靠的服务能力，确保业务连续性"
                },
                "persistentMemory": {
                    "title": "持久记忆",
                    "description": "完整保留业务上下文，对话永不中断"
                },
                "learning": {
                    "title": "持续学习",
                    "description": "在实践中不断成长，越用越智能"
                }
            }
        }
    },
    "auth": {
        "login": "登录",
        "register": "注册",
        "emailOrUsername": "邮箱 / 用户名",
        "emailOrUsernamePlaceholder": "邮箱、用户名或手机号",
        "password": "密码",
        "forgotPassword": "忘记密码？",
        "invalidCredentials": "用户名或密码错误。",
        "serverUnreachable": "无法连接服务器，请检查服务是否正在运行。"
    }
}
```

### 5.2 英文翻译 (en.json)

```json
{
    "login": {
        "hero": {
            "badge": "Enterprise AI Digital Workforce Platform",
            "title": "Intelligent Collaboration",
            "subtitle": "Redefining Enterprise Digitalization",
            "description": "Build professional AI digital employee teams,<br>delivering continuously evolving intelligent services.",
            "features": {
                "multiAgent": {
                    "title": "Team Collaboration",
                    "description": "Intelligent coordination for complex tasks"
                },
                "serviceDelivery": {
                    "title": "Professional Delivery",
                    "description": "Reliable services ensuring business continuity"
                },
                "persistentMemory": {
                    "title": "Persistent Memory",
                    "description": "Complete context retention, never lose a conversation"
                },
                "learning": {
                    "title": "Continuous Learning",
                    "description": "Growing smarter with every interaction"
                }
            }
        }
    },
    "auth": {
        "login": "Login",
        "register": "Register",
        "emailOrUsername": "Email / Username",
        "emailOrUsernamePlaceholder": "Email, username, or phone"
    }
}
```

---

## 6. 关键设计决策

### 6.1 登录标识符字段

**决策**: 使用 `login_identifier` 而非 `email` 或 `username`

**原因**:
- 后端 `UserLogin` schema 支持邮箱、手机号、用户名三种方式登录
- 前端输入框使用 `type="text"` 而非 `type="email"`，避免浏览器强制邮箱格式验证
- 提升用户体验，一个输入框支持多种登录方式

### 6.2 图标库选择

**决策**: 使用 Tabler Icons (`@tabler/icons-react`)

**原因**:
- 专业、现代的设计风格
- React 组件，支持 SVG
- 丰富的图标库
- 轻量且性能好

```tsx
import { IconUsers, IconBrain, IconBuilding, IconRocket } from '@tabler/icons-react';

<IconUsers size={24} stroke={1.5} />
```

### 6.3 品牌名称

**决策**: 使用 `ProudCopilot` 作为品牌名称

**位置**:
- 登录页 Logo 文字
- 浏览器标签标题
- package.json 项目名称

---

## 7. 文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `frontend/src/pages/Login.tsx` | 登录页面组件 |
| `frontend/src/i18n/zh.json` | 中文翻译 |
| `frontend/src/i18n/en.json` | 英文翻译 |
| `frontend/src/index.css` | 登录页样式 |
| `frontend/public/logo-black.png` | Logo 图片 |

---

## 8. 后端 API 对接

### 8.1 登录接口

```
POST /api/auth/login
Content-Type: application/json

{
    "login_identifier": "username 或 email 或 phone",
    "password": "密码",
    "tenant_id": "可选，多租户场景"
}
```

### 8.2 响应格式

**成功响应**:
```json
{
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": { ... },
    "needs_company_setup": false
}
```

**多租户选择响应**:
```json
{
    "requires_tenant_selection": true,
    "login_identifier": "user@example.com",
    "tenants": [
        { "tenant_id": "...", "tenant_name": "公司A", "tenant_slug": "company-a" }
    ]
}
```

---

## 9. 重构注意事项

1. **保留功能卡片**: 4个功能卡片是核心品牌展示，建议保留
2. **图标一致性**: 确保使用专业图标库（Tabler Icons 或类似）
3. **多方式登录**: 支持 `login_identifier` 字段的灵活登录
4. **国际化**: 保持 i18n 结构一致
5. **响应式**: 移动端隐藏左侧品牌区或简化显示
6. **主题色**: 使用深蓝色渐变背景 (`#1e3a8a` → `#2563eb`)

---

*文档生成时间: 2026-04-02*
*版本: v1.8.0-beta.2*
