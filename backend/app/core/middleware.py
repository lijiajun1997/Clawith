"""FastAPI middleware for request tracing, logging, and timeout protection."""

import asyncio
import uuid
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging_config import set_trace_id
from loguru import logger


# Global semaphore to limit concurrent blocking-I/O operations (file scans, subprocess, etc.)
_io_semaphore: asyncio.Semaphore | None = None


def get_io_semaphore() -> asyncio.Semaphore:
    """Lazily create the I/O semaphore (must be called within an event loop)."""
    global _io_semaphore
    if _io_semaphore is None:
        _io_semaphore = asyncio.Semaphore(16)
    return _io_semaphore


# Paths that should bypass the timeout (long-polling, WebSocket upgrade, streaming)
_TIMEOUT_SKIP_PREFIXES = ("/ws/", "/api/ws/", "/api/agents/", "/health")
_TIMEOUT_SKIP_EXACT = ("/api/health",)

DEFAULT_REQUEST_TIMEOUT = 60.0  # seconds


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Middleware: request tracing, logging, and global timeout protection."""

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())[:12]
        set_trace_id(trace_id)
        request.state.trace_id = trace_id

        start_time = time.time()
        client_host = request.client.host if request.client else "-"
        logger.info(f"--> {request.method} {request.url.path} [client: {client_host}]")

        # Skip timeout for WebSocket and streaming endpoints
        path = request.url.path
        skip_timeout = path in _TIMEOUT_SKIP_EXACT or any(
            path.startswith(p) and p not in ("/api/agents/",) for p in _TIMEOUT_SKIP_PREFIXES
        )
        # WebSocket upgrade never gets a timeout
        if request.headers.get("upgrade", "").lower() == "websocket":
            skip_timeout = True

        try:
            if skip_timeout:
                response = await call_next(request)
            else:
                # Wrap with timeout — protects against hung DB queries, slow FS ops, etc.
                response = await asyncio.wait_for(
                    call_next(request),
                    timeout=DEFAULT_REQUEST_TIMEOUT,
                )

            duration = time.time() - start_time
            response.headers["X-Trace-Id"] = trace_id

            # Security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            # CSP: allow inline styles and images from same origin; block inline scripts
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'"
            )

            logger.info(f"<-- {request.method} {request.url.path} {response.status_code} {duration:.3f}s")
            return response

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.warning(
                f"<-- {request.method} {request.url.path} TIMEOUT {duration:.1f}s [trace:{trace_id}]"
            )
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timed out after {DEFAULT_REQUEST_TIMEOUT}s"},
                headers={"X-Trace-Id": trace_id},
            )
        except Exception as exc:
            duration = time.time() - start_time
            logger.error(f"<-- {request.method} {request.url.path} ERROR {duration:.3f}s - {exc}")
            raise
