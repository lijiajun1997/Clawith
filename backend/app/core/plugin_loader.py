"""Plugin loader — 自动发现并加载 plugins/ 目录下的插件后端路由。

使用方式（在 main.py 中添加 2 行）：

    from app.core.plugin_loader import load_plugin_routers
    for name, rtr in load_plugin_routers():
        app.include_router(rtr, prefix=f"{settings.API_PREFIX}/plugins/{name}")
"""

import importlib.util
from pathlib import Path

from fastapi import APIRouter
from loguru import logger

_PLUGINS_DIR = Path(__file__).resolve().parents[3] / "plugins"


def load_plugin_routers() -> list[tuple[str, APIRouter]]:
    """扫描 plugins/ 目录，返回 (plugin_name, router) 列表。

    每个插件子目录如果包含 backend/routes.py 且暴露 `router` 变量，
    就会被加载。以 _ 开头的目录被视为模板/示例，跳过加载。
    """
    result: list[tuple[str, APIRouter]] = []

    if not _PLUGINS_DIR.is_dir():
        return result

    for plugin_dir in sorted(_PLUGINS_DIR.iterdir()):
        # 跳过非目录、隐藏目录、模板目录
        if not plugin_dir.is_dir():
            continue
        if plugin_dir.name.startswith("_") or plugin_dir.name.startswith("."):
            continue

        routes_file = plugin_dir / "backend" / "routes.py"
        if not routes_file.is_file():
            continue

        module_name = f"plugins.{plugin_dir.name}.backend.routes"
        try:
            spec = importlib.util.spec_from_file_location(module_name, routes_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            router = getattr(module, "router", None)
            if router is None:
                logger.warning(f"[plugins] {plugin_dir.name}: routes.py missing `router` export")
                continue

            result.append((plugin_dir.name, router))
            logger.info(f"[plugins] Loaded: {plugin_dir.name}")
        except Exception as e:
            logger.error(f"[plugins] Failed to load {plugin_dir.name}: {e}")

    return result
