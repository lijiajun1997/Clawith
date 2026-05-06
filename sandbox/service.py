"""Clawith Sandbox Service — 常驻代码执行沙箱.

接收 HTTP 请求，在本地 subprocess 中执行代码并返回结果。
支持 Python / Bash / Node.js 三种运行时。

功能对齐后端 SubprocessBackend：
- 安全检查（危险命令/代码模式拦截）
- pip install 自动转换到 shared-deps
- 输出截断 + 溢出文件保存
- WORKSPACE_DIR / AGENT_ROOT 环境变量注入
"""

import asyncio
import os
import re
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
SHARED_DEPS_DIR = Path(os.environ.get("SHARED_DEPS_DIR", "/data/shared-deps"))
AGENTS_DIR = Path(os.environ.get("AGENTS_DIR", "/data/agents"))
DEFAULT_TIMEOUT = int(os.environ.get("DEFAULT_TIMEOUT", "60"))
MAX_TIMEOUT = int(os.environ.get("MAX_TIMEOUT", "300"))
MAX_OUTPUT = int(os.environ.get("MAX_OUTPUT", str(10 * 1024 * 1024)))  # 10 MB

# 输出截断限制（保护 LLM 上下文窗口，与后端 base.py 一致）
MAX_STDOUT_INLINE = 10_000   # 10KB
MAX_STDERR_INLINE = 5_000    # 5KB

# ---------------------------------------------------------------------------
# pip install 自动转换
# ---------------------------------------------------------------------------
_PIP_INSTALL_RE = re.compile(
    r"^\s*!?\s*pip\s+(install\s+)", re.MULTILINE | re.IGNORECASE
)


def _convert_pip_install(code: str) -> str:
    """将 pip install 转为安装到 shared-deps 目录的命令."""
    return _PIP_INSTALL_RE.sub(
        r"python3 -m pip \1--target /data/shared-deps/pip ",
        code,
        count=1,
    )


# ---------------------------------------------------------------------------
# 安全检查（对齐后端 SubprocessBackend）
# ---------------------------------------------------------------------------
_DANGEROUS_BASH_ALWAYS = [
    "rm -rf /", "rm -rf ~", "sudo ", "mkfs", "dd if=",
    ":(){ :", "chmod 777 /", "chown ", "shutdown", "reboot",
]
_DANGEROUS_BASH_NETWORK = [
    "nc ", "ncat ", "ssh ", "scp ",
]
_DANGEROUS_PYTHON_ALWAYS = [
    "shutil.rmtree", "os.system", "os.popen",
    "os.exec", "os.spawn",
]
_DANGEROUS_PYTHON_NETWORK = [
    "socket", "http.client", "ftplib", "smtplib", "telnetlib", "ctypes",
]
_DANGEROUS_NODE_ALWAYS = [
    "child_process", "fs.rmSync", "fs.rmdirSync", "process.exit",
]
_DANGEROUS_NODE_NETWORK = [
    "require('http')", "require('https')", "require('net')",
]


def _check_code_safety(language: str, code: str, allow_network: bool = True) -> str | None:
    """检查代码安全性。返回错误信息或 None（安全）。"""
    code_lower = code.lower()

    if language == "bash":
        for p in _DANGEROUS_BASH_ALWAYS:
            if p.lower() in code_lower:
                return f"Blocked: dangerous command ({p.strip()})"
        if not allow_network:
            for p in _DANGEROUS_BASH_NETWORK:
                if p.lower() in code_lower:
                    return f"Blocked: network command ({p.strip()})"
        if "../../" in code:
            return "Blocked: directory traversal"

    elif language == "python":
        for p in _DANGEROUS_PYTHON_ALWAYS:
            if p.lower() in code_lower:
                return f"Blocked: unsafe operation ({p.strip()})"
        if not allow_network:
            for p in _DANGEROUS_PYTHON_NETWORK:
                if p.lower() in code_lower:
                    return f"Blocked: network operation ({p.strip()})"

    elif language == "node":
        for p in _DANGEROUS_NODE_ALWAYS:
            if p.lower() in code_lower:
                return f"Blocked: unsafe operation ({p})"
        if not allow_network:
            for p in _DANGEROUS_NODE_NETWORK:
                if p.lower() in code_lower:
                    return f"Blocked: network operation ({p.strip()})"

    return None


# ---------------------------------------------------------------------------
# 输出截断 + 溢出文件
# ---------------------------------------------------------------------------
def _truncate_output(text: str, limit: int, work_dir: str | None, prefix: str) -> tuple[str, str | None]:
    """截断输出，溢出部分保存到文件。返回 (truncated_text, overflow_file_path | None)."""
    if len(text) <= limit:
        return text, None

    # 保存完整输出到工作区
    if work_dir:
        try:
            out_dir = Path(work_dir) / "workspace"
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = int(time.time() * 1000)
            file_path = out_dir / f"_exec_{prefix}_{ts}.log"
            file_path.write_text(text, encoding="utf-8")
            rel_path = file_path.relative_to(Path(work_dir)).as_posix()
            return text[:limit], rel_path
        except Exception:
            pass

    return text[:limit], None


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------
class ExecuteRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str = Field(..., pattern=r"^(python|bash|node)$")
    timeout: int = Field(default=30, ge=1, le=300)
    work_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    allow_network: bool = True


class ExecuteResponse(BaseModel):
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    error: str | None = None
    output_file: str | None = None  # 溢出文件路径


# ---------------------------------------------------------------------------
# 执行引擎
# ---------------------------------------------------------------------------
async def _run_code(req: ExecuteRequest) -> ExecuteResponse:
    start = time.time()
    code = req.code

    # 安全检查
    safety_error = _check_code_safety(req.language, code, req.allow_network)
    if safety_error:
        return ExecuteResponse(
            success=False, stdout="", stderr="", exit_code=1,
            duration_ms=0, error=safety_error,
        )

    # pip install 自动转换
    if _PIP_INSTALL_RE.search(code):
        code = _convert_pip_install(code)
        logger.info("Converted pip install command")

    # 解析工作目录
    if req.work_dir:
        cwd = Path(req.work_dir)
    else:
        cwd = Path("/tmp")
    cwd.mkdir(parents=True, exist_ok=True)

    # 构建命令 — 临时脚本写入 /tmp
    ext_map = {"python": (".py", "python3"), "bash": (".sh", "bash"), "node": (".js", "node")}
    ext, runner = ext_map[req.language]
    script = Path("/tmp") / f"_exec_{int(time.time() * 1000)}{ext}"
    script.write_text(code, encoding="utf-8")
    cmd = [runner, str(script)]

    # 构建环境变量（对齐后端 SubprocessBackend）
    env = dict(os.environ)
    env["HOME"] = str(cwd)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    pip_path = str(SHARED_DEPS_DIR / "pip")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pip_path}:{existing}" if existing else pip_path
    env["NODE_PATH"] = str(SHARED_DEPS_DIR / "node_modules")
    env["WORKSPACE_DIR"] = str(cwd)
    # 对齐后端：work_dir 是 agent root，包含 workspace/, skills/, memory/
    if req.work_dir:
        env["AGENT_ROOT"] = req.work_dir
    env.update(req.env)

    timeout = min(req.timeout, MAX_TIMEOUT)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return ExecuteResponse(
                success=False, stdout="", stderr="", exit_code=124,
                duration_ms=int((time.time() - start) * 1000),
                error=f"Execution timed out after {timeout}s",
            )

        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        duration_ms = int((time.time() - start) * 1000)

        # 输出截断（保护 LLM 上下文窗口）
        stdout_truncated, stdout_overflow = _truncate_output(
            stdout_str, MAX_STDOUT_INLINE, req.work_dir, "stdout"
        )
        stderr_truncated, stderr_overflow = _truncate_output(
            stderr_str, MAX_STDERR_INLINE, req.work_dir, "stderr"
        )

        output_file = stdout_overflow or stderr_overflow

        return ExecuteResponse(
            success=proc.returncode == 0,
            stdout=stdout_truncated,
            stderr=stderr_truncated,
            exit_code=proc.returncode or 0,
            duration_ms=duration_ms,
            error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}",
            output_file=output_file,
        )

    except Exception as e:
        return ExecuteResponse(
            success=False, stdout="", stderr="", exit_code=1,
            duration_ms=int((time.time() - start) * 1000),
            error=f"Execution error: {str(e)[:200]}",
        )

    finally:
        try:
            script.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FastAPI 应用
# ---------------------------------------------------------------------------
app = FastAPI(title="Clawith Sandbox", version="1.0.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    return await _run_code(req)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)[:200]},
    )
