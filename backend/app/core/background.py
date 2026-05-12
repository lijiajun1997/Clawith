"""Background task utilities.

Replaces FastAPI BackgroundTasks which is broken by BaseHTTPMiddleware
(Starlette 1.0 silently drops tasks). Uses asyncio.create_task instead.
"""

import asyncio

from loguru import logger


async def _safe_wrapper(coro, name: str):
    """Await a coroutine, logging any exception instead of silently swallowing."""
    try:
        await coro
    except Exception:
        logger.exception("[BG] Background task {} failed", name)


def spawn_background_fn(func, *args, **kwargs):
    """Fire-and-forget a function call with error logging.

    Usage::

        # Instead of:
        #   background_tasks.add_task(func, arg1, arg2)
        # Use:
        #   spawn_background_fn(func, arg1, arg2)
    """
    coro = func(*args, **kwargs)
    name = getattr(coro, "__qualname__", None) or repr(coro)
    return asyncio.create_task(_safe_wrapper(coro, name))
