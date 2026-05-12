[根目录](../CLAUDE.md) > **sandbox**

# Sandbox -- 代码执行沙箱服务

## 模块职责

Sandbox 是一个独立的微服务，负责在安全隔离的环境中执行用户提交的代码。主要功能：
- 接收 HTTP 请求，在本地 subprocess 中执行代码并返回结果
- 支持 Python / Bash / Node.js 三种运行时
- 安全检查：拦截危险命令（rm -rf /、sudo、mkfs 等）和不安全代码模式
- pip install 自动转换到 shared-deps 目录
- 输出截断 + 溢出文件保存（保护 LLM 上下文窗口）
- 工作空间环境变量注入（WORKSPACE_DIR / AGENT_ROOT）

## 入口与启动

- **应用入口**: `service.py` -- 单文件 FastAPI 应用
- **容器镜像**: 基于 `nikolaik/python-nodejs:python3.12-nodejs22-slim`
- **启动命令**: `python3 -m uvicorn service:app --host 0.0.0.0 --port 8888`
- **健康检查**: `GET /health` -> `{"status": "ok"}`

### Docker 构建

```bash
docker build -t clawith-sandbox .
# 端口 8888
```

## 对外接口

### 执行代码

```
POST /execute
Content-Type: application/json

{
  "code": "print('hello')",
  "language": "python",        // python | bash | node
  "timeout": 30,               // 1-300 秒
  "work_dir": "/data/agents/xxx", // 可选，Agent 工作目录
  "env": {},                   // 额外环境变量
  "allow_network": true        // 是否允许网络操作
}
```

响应：

```json
{
  "success": true,
  "stdout": "hello\n",
  "stderr": "",
  "exit_code": 0,
  "duration_ms": 150,
  "error": null,
  "output_file": null          // 溢出文件路径（如有）
}
```

### 安全机制

**Bash 拦截规则**:
- 始终拦截：`rm -rf /`、`sudo`、`mkfs`、`dd if=`、`shutdown`、`reboot`
- 网络模式关闭时额外拦截：`nc`、`ssh`、`scp`
- 目录遍历：`../../`

**Python 拦截规则**:
- 始终拦截：`shutil.rmtree`、`os.system`、`os.popen`、`os.exec`
- 网络模式关闭时额外拦截：`socket`、`http.client`、`smtplib`

**Node.js 拦截规则**:
- 始终拦截：`child_process`、`fs.rmSync`、`process.exit`
- 网络模式关闭时额外拦截：`require('http')`、`require('net')`

### 输出截断

- stdout 内联限制：10KB
- stderr 内联限制：5KB
- 溢出部分保存到 `{work_dir}/workspace/.logs/_exec_{prefix}_{timestamp}.log`

## 关键依赖与配置

### 运行时依赖（`requirements.txt`）

| 类别 | 依赖 |
|------|------|
| Web 框架 | fastapi, uvicorn, loguru |
| 数据分析 | pandas, numpy, scipy, matplotlib |
| 办公文档 | python-docx, python-pptx, openpyxl, xlrd, fpdf2, reportlab |
| 图像处理 | Pillow, pdfplumber |
| 通用 | tqdm, chardet, beautifulsoup4, lxml |
| HTTP | requests, httpx |

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SHARED_DEPS_DIR` | 共享依赖目录 | `/data/shared-deps` |
| `AGENTS_DIR` | Agent 数据目录 | `/data/agents` |
| `DEFAULT_TIMEOUT` | 默认超时（秒） | `60` |
| `MAX_TIMEOUT` | 最大超时（秒） | `300` |
| `MAX_OUTPUT` | 最大输出大小 | `10MB` |

## 数据模型

无数据库。请求和响应使用 Pydantic 模型：

- `ExecuteRequest` -- 执行请求（code, language, timeout, work_dir, env, allow_network）
- `ExecuteResponse` -- 执行结果（success, stdout, stderr, exit_code, duration_ms, error, output_file）

## 测试与质量

- **测试文件**: `test_sandbox.py` -- 沙箱基本功能测试
- 运行测试：`cd sandbox && python -m pytest`

## 常见问题 (FAQ)

**Q: 如何添加新的运行时语言？**
A: 在 `service.py` 的 `ext_map` 中添加语言映射，并更新安全检查规则。

**Q: pip install 是如何工作的？**
A: 代码中的 `pip install` 命令会被自动转换为 `python3 -m pip install --target /data/shared-deps/pip`，安装的包对所有后续执行可见。

## 相关文件清单

```
sandbox/
  service.py          # 完整的沙箱服务（单文件）
  test_sandbox.py     # 测试
  requirements.txt    # Python 依赖
  Dockerfile          # 容器镜像构建
```

## 变更记录 (Changelog)

| 时间 | 操作 | 说明 |
|------|------|------|
| 2026-05-07T13:40:31 | 初始化 | 首次生成模块文档 |
