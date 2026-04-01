"""Local subprocess-based sandbox backend."""

import asyncio
from loguru import logger
import os
import re
import time
from pathlib import Path

from app.services.sandbox.base import BaseSandboxBackend, ExecutionResult, SandboxCapabilities
from app.services.sandbox.config import SandboxConfig


# Security patterns - reused from agent_tools.py
_DANGEROUS_BASH_ALWAYS = [
    "rm -rf /", "rm -rf ~", "sudo ", "mkfs", "dd if=",
    ":(){ :", "chmod 777 /", "chown ", "shutdown", "reboot",
    "python3 -c", "python -c",
]

_DANGEROUS_BASH_NETWORK = [
    "curl ", "wget ", "nc ", "ncat ", "ssh ", "scp ",
]

_DANGEROUS_PYTHON_IMPORTS_ALWAYS = [
    "subprocess", "shutil.rmtree", "os.system", "os.popen",
    "os.exec", "os.spawn",
]

_DANGEROUS_PYTHON_IMPORTS_NETWORK = [
    "socket", "http.client", "urllib.request", "requests",
    "ftplib", "smtplib", "telnetlib", "ctypes",
    "__import__", "importlib",
]

_DANGEROUS_NODE_ALWAYS = [
    "child_process", "fs.rmSync", "fs.rmdirSync", "process.exit",
]

_DANGEROUS_NODE_NETWORK = [
    "require('http')", "require('https')", "require('net')"
]


# ═══════════════════════════════════════════════════════════════════════════
# Skill 依赖安装相关配置
# ═══════════════════════════════════════════════════════════════════════════

# 全局 Skill 依赖目录
SKILL_PACKAGES_DIR = os.environ.get("PIP_TARGET_DIR", "/data/skill_packages")

# pip 镜像源（默认清华镜像）
DEFAULT_PIP_INDEX_URL = os.environ.get(
    "PIP_INDEX_URL",
    "https://pypi.tuna.tsinghua.edu.cn/simple"
)

# 允许安装的包白名单（空列表表示允许所有）
ALLOWED_PACKAGES: list[str] = []

# 禁止安装的包黑名单（安全隐患）
BLOCKED_PACKAGES = [
    "pwn", "pwntools",  # CTF/渗透测试工具
    "rat", "keylogger",  # 恶意软件
    "malware", "backdoor",
    "rootkit",
]

# ═══════════════════════════════════════════════════════════════════════════


def _check_code_safety(language: str, code: str, allow_network: bool = False) -> str | None:
    """Check code for dangerous patterns. Returns error message if unsafe, None if ok."""
    code_lower = code.lower()

    if language == "bash":
        # Always check dangerous patterns
        for pattern in _DANGEROUS_BASH_ALWAYS:
            if pattern.lower() in code_lower:
                logger.warning(f"Blocked: dangerous command detected ({pattern.strip()})")
                return f"Blocked: dangerous command detected ({pattern.strip()})"
        # Network commands only when network is not allowed
        if not allow_network:
            for pattern in _DANGEROUS_BASH_NETWORK:
                if pattern.lower() in code_lower:
                    logger.warning(f"Blocked: network command not allowed ({pattern.strip()})")        
                    return f"Blocked: network command not allowed ({pattern.strip()})"
        if "../../" in code:
            return "Blocked: directory traversal not allowed"

    elif language == "python":
        # Always check dangerous patterns
        for pattern in _DANGEROUS_PYTHON_IMPORTS_ALWAYS:
            if pattern.lower() in code_lower:
                logger.warning(f"Blocked: unsafe operation detected ({pattern.strip()})")
                return f"Blocked: unsafe operation detected ({pattern.strip()})"
        # Network imports only when network is not allowed
        if not allow_network:
            for pattern in _DANGEROUS_PYTHON_IMPORTS_NETWORK:
                if pattern.lower() in code_lower:
                    logger.warning(f"Blocked: network operation not allowed ({pattern.strip()})")
                    return f"Blocked: network operation not allowed ({pattern.strip()})"

    elif language == "node":
        # Always check dangerous patterns
        for pattern in _DANGEROUS_NODE_ALWAYS:
            if pattern.lower() in code_lower:
                return f"Blocked: unsafe operation detected ({pattern})"
        # Network requires only when network is not allowed
        if not allow_network:
            for pattern in _DANGEROUS_NODE_NETWORK:
                if pattern.lower() in code_lower:
                    logger.warning(f"Blocked: network operation not allowed ({pattern.strip()})")
                    return f"Blocked: network operation not allowed ({pattern.strip()})"

    return None


# ═══════════════════════════════════════════════════════════════════════════
# pip 命令检测和处理函数
# ═══════════════════════════════════════════════════════════════════════════

def _extract_pip_packages(code: str) -> list[str]:
    """从 pip install 命令中提取包名列表。

    Args:
        code: bash 或 python 代码

    Returns:
        包名列表
    """
    packages = []

    # 匹配 pip install 后面的包名
    # 支持: pip install pkg, pip install pkg==1.0, pip install pkg>=1.0
    patterns = [
        r'pip\d*\s+install\s+([^\s;|&><]+)',  # bash 格式
        r'subprocess.*pip.*install.*?([a-zA-Z0-9_-]+)',  # subprocess 调用
    ]

    for pattern in patterns:
        matches = re.findall(pattern, code, re.IGNORECASE)
        for match in matches:
            # 提取纯包名（去掉版本号）
            pkg_name = re.split(r'[=<>!~\[]', match)[0].strip()
            if pkg_name and pkg_name not in ['-', '--', '-r', '-U', '-q', '--quiet']:
                packages.append(pkg_name.lower())

    return packages


def _check_pip_safety(code: str) -> str | None:
    """检查 pip install 命令的安全性。

    Args:
        code: 待执行的代码

    Returns:
        错误消息，如果安全则返回 None
    """
    packages = _extract_pip_packages(code)

    for pkg in packages:
        # 检查黑名单
        if pkg in BLOCKED_PACKAGES:
            return f"Blocked: package '{pkg}' is in the blocked list (security risk)"

        # 检查白名单（如果配置了）
        if ALLOWED_PACKAGES and pkg not in ALLOWED_PACKAGES:
            return f"Blocked: package '{pkg}' is not in the allowed list"

    return None


def _build_safe_pip_command(original_code: str) -> str:
    """构建安全的 pip 安装命令。

    将用户代码中的 pip install 转换为带有全局配置的安全命令。

    Args:
        original_code: 原始代码

    Returns:
        修改后的代码
    """
    # 确保目标目录存在
    os.makedirs(SKILL_PACKAGES_DIR, exist_ok=True)

    modified_code = original_code

    # 如果没有指定 --target，添加它
    if "--target" not in original_code and "-t " not in original_code:
        modified_code = modified_code.replace(
            "pip install",
            f"pip install --target={SKILL_PACKAGES_DIR}"
        )
        modified_code = modified_code.replace(
            "pip3 install",
            f"pip3 install --target={SKILL_PACKAGES_DIR}"
        )

    # 如果没有指定 --index-url 或 -i，添加默认镜像
    if "--index-url" not in original_code and "-i " not in original_code:
        modified_code = modified_code.replace(
            "pip install",
            f"pip install --index-url={DEFAULT_PIP_INDEX_URL}"
        )
        modified_code = modified_code.replace(
            "pip3 install",
            f"pip3 install --index-url={DEFAULT_PIP_INDEX_URL}"
        )

    return modified_code


def _is_pip_install_command(code: str, language: str) -> bool:
    """检测代码是否为 pip install 命令。

    Args:
        code: 代码内容
        language: 代码语言

    Returns:
        是否为 pip install 命令
    """
    if language != "bash":
        return False

    code_lower = code.lower()
    return "pip" in code_lower and "install" in code_lower


# ═══════════════════════════════════════════════════════════════════════════


class SubprocessBackend(BaseSandboxBackend):
    """Local subprocess-based sandbox backend.

    This backend executes code in a subprocess within the agent's workspace.
    It provides basic security checks but no process isolation.
    """

    name = "subprocess"

    def __init__(self, config: SandboxConfig):
        self.config = config

    def get_capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            supported_languages=["python", "bash", "node"],
            max_timeout=self.config.max_timeout,
            max_memory_mb=256,
            network_available=self.config.allow_network,
            filesystem_available=True,
        )

    async def health_check(self) -> bool:
        """Check if basic system commands are available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    async def execute(
        self,
        code: str,
        language: str,
        timeout: int = 30,
        work_dir: str | None = None,
        **kwargs
    ) -> ExecutionResult:
        """Execute code in a subprocess."""
        start_time = time.time()

        # Validate language
        if language not in ("python", "bash", "node"):
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=1,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"Unsupported language: {language}. Use: python, bash, or node"
            )

        # ═════════════════════════════════════════════════════════════════════
        # pip install 特殊处理
        # ═════════════════════════════════════════════════════════════════════
        is_pip_install = _is_pip_install_command(code, language)

        if is_pip_install:
            # pip install 安全检查
            pip_safety_error = _check_pip_safety(code)
            if pip_safety_error:
                logger.warning(f"[Subprocess] Pip install blocked: {pip_safety_error}")
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=1,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"❌ {pip_safety_error}"
                )

            # 构建安全的 pip 命令
            code = _build_safe_pip_command(code)
            logger.info(f"[Subprocess] Pip install: modified with target={SKILL_PACKAGES_DIR}")
        # ═════════════════════════════════════════════════════════════════════

        # Security check - pass allow_network config
        safety_error = _check_code_safety(language, code, self.config.allow_network)
        if safety_error:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=1,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"❌ {safety_error}"
            )

        # Determine work directory
        if work_dir:
            work_path = Path(work_dir)
        else:
            work_path = Path.cwd() / "workspace"
        work_path.mkdir(parents=True, exist_ok=True)

        # Determine command and file extension
        if language == "python":
            ext = ".py"
            cmd_prefix = ["python3"]
        elif language == "bash":
            ext = ".sh"
            cmd_prefix = ["bash"]
        elif language == "node":
            ext = ".js"
            cmd_prefix = ["node"]

        # Write code to temp file
        script_path = work_path / f"_exec_tmp{ext}"

        try:
            script_path.write_text(code, encoding="utf-8")

            # Set up safe environment
            safe_env = dict(os.environ)
            safe_env["HOME"] = str(work_path)
            safe_env["PYTHONDONTWRITEBYTECODE"] = "1"

            # ═════════════════════════════════════════════════════════════════
            # 清除代理环境变量，避免 pip 连接代理失败
            # ═════════════════════════════════════════════════════════════════
            for proxy_var in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"]:
                safe_env.pop(proxy_var, None)
            # ═════════════════════════════════════════════════════════════════

            # ═════════════════════════════════════════════════════════════════
            # 为 Python 代码设置 PYTHONPATH，包含 Skill 依赖目录
            # ═════════════════════════════════════════════════════════════════
            if language == "python":
                existing_pythonpath = safe_env.get("PYTHONPATH", "")
                if existing_pythonpath:
                    safe_env["PYTHONPATH"] = f"{SKILL_PACKAGES_DIR}:{existing_pythonpath}"
                else:
                    safe_env["PYTHONPATH"] = SKILL_PACKAGES_DIR
            # ═════════════════════════════════════════════════════════════════

            # Execute
            proc = await asyncio.create_subprocess_exec(
                *cmd_prefix, str(script_path),
                cwd=str(work_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    exit_code=124,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=f"Code execution timed out after {timeout}s"
                )

            stdout_str = stdout.decode("utf-8", errors="replace")[:10000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:5000]

            duration_ms = int((time.time() - start_time) * 1000)

            # ═════════════════════════════════════════════════════════════════
            # pip install 成功后记录日志
            # ═════════════════════════════════════════════════════════════════
            if is_pip_install and proc.returncode == 0:
                logger.info(f"[Subprocess] Pip install succeeded: installed to {SKILL_PACKAGES_DIR}")
            # ═════════════════════════════════════════════════════════════════

            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                error=None if proc.returncode == 0 else f"Exit code: {proc.returncode}"
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"[Subprocess] Execution error")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=1,
                duration_ms=duration_ms,
                error=f"Execution error: {str(e)[:200]}"
            )

        finally:
            # Clean up temp script
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass