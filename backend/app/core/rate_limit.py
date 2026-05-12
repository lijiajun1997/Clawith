"""Simple Redis-based rate limiter for sensitive endpoints."""

from fastapi import HTTPException, Request, status
from loguru import logger


async def _check_rate_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    """Check rate limit using Redis INCR + EXPIRE. Returns True if allowed."""
    from app.core.events import get_redis

    try:
        r = await get_redis()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)
        return count <= max_requests
    except Exception:
        # Redis unavailable — allow request (fail open)
        logger.warning("Rate limit check failed (Redis unavailable), allowing request")
        return True


def auth_rate_limit(max_requests: int = 5, window_seconds: int = 300):
    """FastAPI dependency that rate-limits by client IP.

    Usage:
        @router.post("/login", dependencies=[Depends(auth_rate_limit(5, 300))])
    """
    async def _dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:auth:{client_ip}:{request.url.path}"
        allowed = await _check_rate_limit(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
    return _dependency
