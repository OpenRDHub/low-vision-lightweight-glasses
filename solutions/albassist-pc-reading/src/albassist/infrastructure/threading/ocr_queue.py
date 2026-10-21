"""OCR 请求有界队列（容量 2，单并发）。"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class OcrRequestQueue(Generic[T]):
    """OCR 请求有界队列。

    满则丢弃最旧请求，单并发消费。
    """

    capacity: int = 2
    _queue: deque[T] = field(default_factory=lambda: deque(maxlen=2), init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _not_empty: threading.Condition = field(init=False)
    _dropped_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self._queue = deque(maxlen=self.capacity)
        self._not_empty = threading.Condition(self._lock)

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def put(self, item: T) -> None:
        """放入请求，满则丢弃最旧。"""
        with self._lock:
            if len(self._queue) >= self.capacity:
                self._queue.popleft()
                self._dropped_count += 1
            self._queue.append(item)
            self._not_empty.notify()

    def take(self, timeout: float | None = None) -> T | None:
        """取出请求，阻塞等待。"""
        with self._not_empty:
            while not self._queue:
                if not self._not_empty.wait(timeout=timeout):
                    return None
            return self._queue.popleft()

    def clear(self) -> None:
        """清空队列。"""
        with self._lock:
            self._queue.clear()