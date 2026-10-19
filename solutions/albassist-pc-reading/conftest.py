"""pytest 全局配置。

Windows 下优先使用 SelectorEventLoopPolicy。在受限沙箱中 socketpair
不可用时，跳过 async 测试（含 @pytest.mark.asyncio 标记和手动
asyncio.run 调用）而非报错，保证非 async 测试仍可运行。
"""

from __future__ import annotations

import asyncio
import inspect
import sys

import pytest


def _can_create_event_loop() -> bool:
    try:
        loop = asyncio.new_event_loop()
        loop.close()
        return True
    except Exception:
        return False


_ASYNC_AVAILABLE = _can_create_event_loop()

if sys.platform == "win32" and _ASYNC_AVAILABLE:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _ASYNC_AVAILABLE:
        return
    skip = pytest.mark.skip(reason="asyncio 事件循环在当前环境不可用（socketpair 受限）")
    for item in items:
        if item.get_closest_marker("asyncio") is not None:
            item.add_marker(skip)
            continue
        obj = getattr(item, "obj", None)
        if obj is not None:
            try:
                source = inspect.getsource(obj)
                if "asyncio.run" in source or "asyncio.new_event_loop" in source:
                    item.add_marker(skip)
            except (OSError, TypeError):
                pass