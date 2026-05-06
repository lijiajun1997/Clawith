"""Pool-based sandbox backend (calls clawith-sandbox-service)."""

import time

import httpx

from app.services.sandbox.base import BaseSandboxBackend, ExecutionResult, SandboxCapabilities
from app.services.sandbox.config import SandboxConfig
from loguru import logger


class PoolSandboxBackend(BaseSandboxBackend):
    """Dedicated sandbox service backend.

    Connects to the clawith-sandbox Docker Compose service for
    hot-start code execution with pre-installed dependencies.

    Configuration:
    - SANDBOX_API_URL: URL of sandbox service (e.g., http://sandbox:8888)
    """

    name = "pool_sandbox"

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.base_url = config.api_url.rstrip("/") if config.api_url else ""

        if not self.base_url:
            raise ValueError(
                "pool_sandbox requires SANDBOX_API_URL "
                "(e.g., http://sandbox:8888)."
            )

    def get_capabilities(self) -> SandboxCapabilities:
        return SandboxCapabilities(
            supported_languages=["python", "bash", "node"],
            max_timeout=self.config.max_timeout,
            max_memory_mb=512,
            network_available=self.config.allow_network,
            filesystem_available=True,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.base_url}/health", timeout=5.0
                )
                return resp.status_code == 200
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
        start_time = time.time()

        payload = {
            "code": code,
            "language": language,
            "timeout": min(timeout, self.config.max_timeout),
            "allow_network": self.config.allow_network,
        }
        if work_dir:
            payload["work_dir"] = work_dir

        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/execute",
                    json=payload,
                    headers=headers,
                    timeout=float(timeout + 10),
                )

                if resp.status_code != 200:
                    return ExecutionResult(
                        success=False, stdout="", stderr="",
                        exit_code=resp.status_code,
                        duration_ms=int((time.time() - start_time) * 1000),
                        error=f"sandbox error: HTTP {resp.status_code} - {resp.text[:200]}",
                    )

                data = resp.json()
                return ExecutionResult(
                    success=data.get("success", False),
                    stdout=data.get("stdout", ""),
                    stderr=data.get("stderr", ""),
                    exit_code=data.get("exit_code", 1),
                    duration_ms=data.get("duration_ms", int((time.time() - start_time) * 1000)),
                    error=data.get("error"),
                    output_file=data.get("output_file"),
                )

        except httpx.TimeoutException:
            return ExecutionResult(
                success=False, stdout="", stderr="", exit_code=124,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"Code execution timed out after {timeout}s",
            )

        except Exception as e:
            logger.exception(f"[PoolSandbox] Execution error")
            return ExecutionResult(
                success=False, stdout="", stderr="", exit_code=1,
                duration_ms=int((time.time() - start_time) * 1000),
                error=f"sandbox error: {str(e)[:200]}",
            )
