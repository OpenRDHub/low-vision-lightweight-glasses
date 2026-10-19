"""LatestFrameBuffer 测试。"""

from __future__ import annotations

from albassist.infrastructure.threading.frame_buffer import LatestFrameBuffer


class TestLatestFrameBuffer:
    def test_put_take(self) -> None:
        buf: LatestFrameBuffer[int] = LatestFrameBuffer()
        buf.put(42)
        assert buf.take() == 42
        assert buf.take() is None

    def test_put_overwrites(self) -> None:
        buf: LatestFrameBuffer[int] = LatestFrameBuffer()
        buf.put(1)
        buf.put(2)
        buf.put(3)
        assert buf.take() == 3
        assert buf.dropped_count == 2

    def test_peek(self) -> None:
        buf: LatestFrameBuffer[int] = LatestFrameBuffer()
        buf.put(42)
        assert buf.peek() == 42
        assert buf.peek() == 42

    def test_clear(self) -> None:
        buf: LatestFrameBuffer[int] = LatestFrameBuffer()
        buf.put(42)
        buf.clear()
        assert buf.take() is None

    def test_empty_take(self) -> None:
        buf: LatestFrameBuffer[int] = LatestFrameBuffer()
        assert buf.take() is None