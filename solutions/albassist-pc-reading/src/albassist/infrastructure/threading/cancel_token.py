"""取消令牌基础设施 - 协作式取消。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass
class CancellationToken:
    """协作式取消令牌。

    cancel() 后后续 throw_if_cancelled_async() 抛 asyncio.CancelledError。
    UI 取消时调用 cancel() 立即恢复不等待原生推理。
    """

    _cancelled: bool = field(default=False, init=False)

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """标记为已取消。"""
        self._cancelled = True

    def reset(self) -> None:
        """重置取消状态。"""
        self._cancelled = False

    async def throw_if_cancelled_async(self) -> None:
        """如果已取消则抛出 CancelledError。"""
        if self._cancelled:
            raise asyncio.CancelledError("操作已被取消")

    async def wait_or_cancel_async(self, timeout: float) -> bool:
        """等待指定时间或被取消。

        Returns:
            True 如果正常等待结束，False 如果被取消。
        """
        try:
            await asyncio.wait_for(self._wait_cancel(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return True
        except asyncio.CancelledError:
            return False

    async def _wait_cancel(self) -> None:
        while not self._cancelled:
            await asyncio.sleep(0.01)