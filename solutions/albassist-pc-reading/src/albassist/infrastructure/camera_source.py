"""本地与局域网相机采集适配器。

本地设备使用 ``cv2.VideoCapture``，MJPEG 网络摄像头使用标准库 HTTP
读取并按 JPEG 起止标记拆帧。两种输入都通过同一个 ImageFrame 端口输出，
上层不感知设备类型。
"""

from __future__ import annotations

import threading
import urllib.parse
import urllib.request
from typing import Any, Callable

import cv2
import numpy as np

from albassist.application.ports.camera_source import CameraDevice
from albassist.domain.exceptions import CameraDisconnectedError, CameraPermissionDeniedError
from albassist.domain.models.image_frame import ImageFrame
from albassist.infrastructure.threading.frame_buffer import LatestFrameBuffer
from albassist.vision.opencv_image_importer import OpenCvImageImporter


_MJPEG_DEVICE_PREFIX = "mjpeg|"


class CameraSourceAdapter:
    """相机采集适配器 - 实现 ICameraSource 语义。

    后台线程采集，LatestFrameBuffer（容量 1）最新帧优先，
    通过回调通知主线程，相机断开通过回调通知不抛异常。
    """

    def __init__(self, network_camera_urls: tuple[str, ...] = ()) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._network_camera_urls = tuple(
            url.strip() for url in network_camera_urls if url.strip()
        )
        self._buffer: LatestFrameBuffer[ImageFrame] = LatestFrameBuffer()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._on_frame: Callable[[ImageFrame], None] | None = None
        self._on_error: Callable[[str], None] | None = None
        self._importer = OpenCvImageImporter()

    async def list_async(self, cancel_token: object | None = None) -> list[CameraDevice]:
        """枚举本地相机。

        网络 MJPEG 地址通过显式 ``mjpeg|URL`` 传入，不在枚举阶段扫描局域网，
        避免网络探测阻塞界面或意外访问其他设备。
        """
        devices: list[CameraDevice] = [
            CameraDevice(
                device_id=f"{_MJPEG_DEVICE_PREFIX}{url}",
                name=f"智能眼镜摄像头 (MJPEG)",
                is_available=True,
            )
            for url in self._network_camera_urls
        ]
        empty_count = 0
        for idx in range(4):
            if getattr(cancel_token, "is_cancelled", False):
                break
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            try:
                if cap.isOpened():
                    devices.append(
                        CameraDevice(
                            device_id=str(idx),
                            name=f"本地相机 {idx + 1}",
                            is_available=True,
                        )
                    )
                    empty_count = 0
                else:
                    empty_count += 1
            finally:
                cap.release()
            if empty_count >= 2:
                break
        return devices

    async def start_async(
        self,
        device_id: str,
        on_frame: Callable[[ImageFrame], None],
        cancel_token: object | None = None,
    ) -> None:
        """启动本地或 MJPEG 网络相机采集。"""
        if not callable(on_frame):
            raise TypeError("on_frame 必须是可调用对象")
        await self.stop_async()
        self._on_frame = on_frame
        self._stop_event.clear()
        self._buffer.clear()

        if device_id.startswith(_MJPEG_DEVICE_PREFIX):
            url = device_id[len(_MJPEG_DEVICE_PREFIX):].strip()
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                self._stop_event.set()
                raise ValueError("MJPEG 地址必须是完整的 http(s) URL")
            target: Callable[..., object] = self._mjpeg_loop
            args: tuple[object, ...] = (url,)
        else:
            try:
                idx = int(device_id)
            except (TypeError, ValueError) as exc:
                self._stop_event.set()
                raise ValueError("本地相机设备 ID 必须是非负整数") from exc
            if idx < 0:
                self._stop_event.set()
                raise ValueError("本地相机设备 ID 不能为负数")
            capture = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not capture.isOpened():
                capture.release()
                self._stop_event.set()
                raise CameraPermissionDeniedError(f"无法打开相机 {device_id}")
            self._capture = capture
            target = self._capture_loop
            args = ()

        self._thread = threading.Thread(
            target=target, args=args, daemon=True, name="camera-capture"
        )
        self._thread.start()

    async def stop_async(self, cancel_token: object | None = None) -> None:
        """停止相机采集。"""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    async def aclose(self) -> None:
        await self.stop_async()

    def set_error_callback(self, on_error: Callable[[str], None]) -> None:
        self._on_error = on_error

    def _capture_loop(self) -> None:
        """本地相机采集循环（后台线程）。"""
        while not self._stop_event.is_set() and self._capture is not None:
            try:
                ret, frame = self._capture.read()
            except Exception as exc:
                self._report_error(f"本地相机读取失败: {exc}")
                break
            if not ret:
                self._report_error("相机断开")
                break
            self._emit_numpy_frame(frame)

    def _mjpeg_loop(self, url: str) -> None:
        """读取 multipart 或连续 JPEG 响应，按 JPEG 标记拆出完整帧。"""
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Albassist/0.1", "Accept": "multipart/x-mixed-replace,image/jpeg"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                buffer = bytearray()
                while not self._stop_event.is_set():
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        self._report_error("MJPEG 摄像头连接已关闭")
                        break
                    buffer.extend(chunk)
                    while not self._stop_event.is_set():
                        start = buffer.find(b"\xff\xd8")
                        if start < 0:
                            if len(buffer) > 2 * 1024 * 1024:
                                del buffer[:-2]
                            break
                        end = buffer.find(b"\xff\xd9", start + 2)
                        if end < 0:
                            if start > 0:
                                del buffer[:start]
                            break
                        jpeg = bytes(buffer[start:end + 2])
                        del buffer[:end + 2]
                        image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if image is not None:
                            self._emit_numpy_frame(image)
        except Exception as exc:
            if not self._stop_event.is_set():
                self._report_error(f"MJPEG 摄像头连接失败: {exc}")

    def _emit_numpy_frame(self, frame: np.ndarray[Any, Any]) -> None:
        try:
            image_frame = self._importer.from_numpy_array(frame)
            self._buffer.put(image_frame)
            item = self._buffer.take()
            if item is not None and self._on_frame is not None:
                self._on_frame(item)
        except Exception as exc:
            self._report_error(f"相机帧转换失败: {exc}")

    def _report_error(self, message: str) -> None:
        self._stop_event.set()
        if self._on_error is not None:
            try:
                self._on_error(message)
            except Exception:
                pass

    @property
    def dropped_count(self) -> int:
        return self._buffer.dropped_count