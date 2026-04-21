"""Local subprocess-based sandbox backend."""

import asyncio
from loguru import logger
import os
import time
from pathlib import Path

from app.services.sandbox.base import BaseSandboxBackend, ExecutionResult, SandboxCapabilities
from app.services.sandbox.config import SandboxConfig

# Global shared dependencies directory (persisted via Docker volume)
_SHARED_DEPS_DIR = os.environ.get("SHARED_DEPS_DIR", "/data/shared-deps")

# Platform-aware path separator for PYTHONPATH
_PATH_SEP = os.pathsep  # ';' on Windows, ':' on Linux/macOS


def _ensure_deps_dirs() -> None:
    """Ensure shared dependency directories exist (no-op if path is not writable)."""
    for subdir in ("pip", "node_modules"):
        d = Path(_SHARED_DEPS_DIR) / subdir
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # May not be writable in all environments (e.g. Windows dev)


_ensure_deps_dirs()

# Security patterns - allow office-scenario dependencies (pip install, requests, python scripts)
_DANGEROUS_BASH_ALWAYS = [
    "rm -rf /", "rm -rf ~", "sudo ", "mkfs", "dd if=",
    ":(){ :", "chmod 777 /", "chown ", "shutdown", "reboot",
    # Removed: "python3 -c", "python -c" — allow bash to invoke python scripts
]

_DANGEROUS_BASH_NETWORK = [
    "nc ", "ncat ", "ssh ", "scp ",
    # Removed: "curl ", "wget " — allow downloading dependencies
]

_DANGEROUS_PYTHON_IMPORTS_ALWAYS = [
    # Removed: "subprocess" — allow pip install via subprocess.run([sys.executable, "-m", "pip", ...])
    # Agent needs to install packages during execution
    "shutil.rmtree", "os.system", "os.popen",
    "os.exec", "os.spawn",
]

_DANGEROUS_PYTHON_IMPORTS_NETWORK = [
    "socket", "http.client", "ftplib", "smtplib", "telnetlib", "ctypes",
    # Removed: "requests", "urllib.request" — office scenarios need HTTP
    # Removed: "__import__", "importlib" — pip install needs these
]

_DANGEROUS_NODE_ALWAYS = [
    "child_process", "fs.rmSync", "fs.rmdirSync", "process.exit",
]

_DANGEROUS_NODE_NETWORK = [
    "require('http')", "require('https')", "require('net')"
]


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

        # Determine work directory: use agent root (not workspace/) so that
        # Agent's code can use natural paths like "workspace/", "skills/", "memory/"
        if work_dir:
            agent_root = Path(work_dir)
        else:
            agent_root = Path.cwd()

        # Use agent_root as work_dir so relative paths work intuitively
        work_path = agent_root
        work_path.mkdir(parents=True, exist_ok=True)

        # Determine command and file extension
        if language == "python":
            ext = ".py"
            cmd_prefix = ["python3"]
        elif language == "bash":
            ext = ".sh"
            cmd_prefix = ["bash"]
            # Auto-convert pip install commands: pip install -> python3 -m pip install
            # Supports both formats: `pip install` or `!pip install` (Jupyter style)
            import re
            if re.search(r'^\s*!?\s*pip\s+install', code, re.MULTILINE | re.IGNORECASE):
                # Replace only 'pip' with 'python3 -m pip', keep the rest intact
                code = re.sub(r'^\s*!?\s*(pip)\s+', r'python3 -m \1 ', code, count=1, flags=re.MULTILINE | re.IGNORECASE)
                logger.info(f"[SubprocessBackend] Auto-converted pip command to: {code.strip()}")
        elif language == "node":
            ext = ".js"
            cmd_prefix = ["node"]

        # Write code to temp file
        script_path = work_path / f"_exec_tmp{ext}"

        try:
            script_path.write_text(code, encoding="utf-8")

            # Set up safe environment with shared dependency paths
            safe_env = dict(os.environ)
            safe_env["HOME"] = str(work_path)
            safe_env["PYTHONDONTWRITEBYTECODE"] = "1"

            # Inject paths so code can find its files without knowing absolute paths
            safe_env["WORKSPACE_DIR"] = str(work_path)      # workspace/ absolute path
            safe_env["AGENT_ROOT"] = str(agent_root)         # agent root (skills/, etc.)

            # Inject global shared deps into PYTHONPATH so installed packages are importable
            pip_deps = f"{_SHARED_DEPS_DIR}/pip"
            existing_pp = safe_env.get("PYTHONPATH", "")
            safe_env["PYTHONPATH"] = f"{pip_deps}{_PATH_SEP}{existing_pp}" if existing_pp else pip_deps
            safe_env["NODE_PATH"] = f"{_SHARED_DEPS_DIR}/node_modules"

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

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            duration_ms = int((time.time() - start_time) * 1000)

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