"""最新帧优先有界缓冲（容量 1）。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class LatestFrameBuffer(Generic[T]):
    """线程安全的最新帧缓冲。

    put 覆盖旧帧并计数丢弃，take 取出清空。
    容量 1，保证预览使用最新帧，不积压长视频队列。
    """

    _item: T | None = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _dropped_count: int = field(default=0, init=False)

    @property
    def dropped_count(self) -> int:
        """被丢弃的帧数。"""
        return self._dropped_count

    def put(self, item: T) -> None:
        """放入帧，覆盖旧帧。"""
        with self._lock:
            if self._item is not None:
                self._dropped_count += 1
            self._item = item

    def take(self) -> T | None:
        """取出帧并清空。"""
        with self._lock:
            item = self._item
            self._item = None
            return item

    def peek(self) -> T | None:
        """查看当前帧但不取出。"""
        with self._lock:
            return self._item

    def clear(self) -> None:
        """清空缓冲。"""
        with self._lock:
            self._item = None