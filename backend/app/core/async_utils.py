"""Utilities for safely running blocking I/O in async context.

All sync filesystem, subprocess, or CPU-bound work should go through
`run_sync()` so that:
  1. It runs in a thread pool (never blocks the event loop)
  2. Concurrency is bounded by the global I/O semaphore
  3. A per-call timeout prevents runaway operations
"""

import asyncio
import functools
from typing import Any, Callable, ParamSpec, TypeVar

from loguru import logger

P = ParamSpec("P")
T = TypeVar("T")

DEFAULT_SYNC_TIMEOUT = 30.0  # seconds per blocking call


async def run_sync(
    func: Callable[..., T],
    *args: Any,
    timeout: float = DEFAULT_SYNC_TIMEOUT,
    **kwargs: Any,
) -> T:
    """Run a sync callable in the thread pool with semaphore + timeout.

    Usage:
        result = await run_sync(my_blocking_func, arg1, arg2)
        # or with a custom timeout:
        result = await run_sync(scan_directory, path, timeout=10)
    """
    from app.core.middleware import get_io_semaphore

    sem = get_io_semaphore()

    async def _guarded() -> T:
        async with sem:
            return await asyncio.to_thread(func, *args, **kwargs)

    try:
        return await asyncio.wait_for(_guarded(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"run_sync timed out after {timeout}s: {func.__name__}")
        raise
