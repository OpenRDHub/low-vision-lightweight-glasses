"""局域网 MJPEG 摄像头适配器测试。"""

from __future__ import annotations

import asyncio

import cv2
import numpy as np
import pytest

from albassist.infrastructure.camera_source import CameraSourceAdapter


NETWORK_URL = "http://192.168.84.243:8080/stream.mjpg"


def test_list_includes_explicit_network_camera() -> None:
    adapter = CameraSourceAdapter((NETWORK_URL,))
    devices = asyncio.run(adapter.list_async())

    assert devices[0].device_id == f"mjpeg|{NETWORK_URL}"
    assert devices[0].is_available is True


def test_start_rejects_invalid_mjpeg_url() -> None:
    async def run() -> None:
        adapter = CameraSourceAdapter()
        with pytest.raises(ValueError, match=r"完整的 http\(s\) URL"):
            await adapter.start_async("mjpeg|not-a-url", lambda _frame: None)

    asyncio.run(run())


def test_mjpeg_loop_decodes_jpeg_and_emits_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    ok, encoded = cv2.imencode(".jpg", np.zeros((8, 12, 3), dtype=np.uint8))
    assert ok

    class _Response:
        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            if self.read_once:
                return b""
            self.read_once = True
            return b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes()

        read_once = False

    response = _Response()
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: response)

    frames = []
    adapter = CameraSourceAdapter()
    adapter._stop_event.clear()
    adapter._on_frame = frames.append  # type: ignore[attr-defined]
    adapter._mjpeg_loop(NETWORK_URL)  # type: ignore[attr-defined]

    assert len(frames) == 1
    assert frames[0].width == 12
    assert frames[0].height == 8
