"""人脸提醒工作线程（P2）。

后台线程驱动 IFaceDetector.detect_async，按人数变化与冷却时间节流，
通过 ITtsEngine.speak_async 离线语音播报。不阻塞相机帧管线。
"""

from __future__ import annotations


import queue
import threading
import time

from albassist.application.ports.face_detector import IFaceDetector
from albassist.application.ports.tts_engine import ITtsEngine
from albassist.domain.models.image_frame import ImageFrame


class FaceAlertWorker:
    """人脸提醒工作器 - 后台线程检测 + 节流播报。"""

    def __init__(
        self,
        detector: IFaceDetector,
        tts: ITtsEngine,
        cooldown_seconds: float = 5.0,
    ) -> None:
        self._detector = detector
        self._tts = tts
        self._cooldown = cooldown_seconds
        self._frame_queue: queue.Queue[ImageFrame] = queue.Queue(maxsize=1)
        self._thread: threading.Thread | None = None
        self._running = False
        self._enabled = False
        self._last_count = -1
        self._last_speak_time = 0.0
        self._lock = threading.Lock()

    @property
    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._enabled = enabled
            if not enabled:
                self._last_count = -1

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._work_loop, daemon=True, name="face-alert-worker"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        with self._frame_queue.mutex:
            self._frame_queue.queue.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def on_frame(self, frame: ImageFrame) -> None:
        """投递最新帧（覆盖式，丢弃旧帧防堆积）。"""
        if not self.is_enabled:
            return
        q = self._frame_queue
        with q.mutex:
            q.queue.clear()
            q.queue.append(frame)

    def _work_loop(self) -> None:
        try:
            self._detector.warmup()  # type: ignore[attr-defined]
        except Exception:
            pass

        while self._running:
            try:
                frame = self._frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if not self.is_enabled:
                continue

            try:
                result = self._detector.detect(frame)  # type: ignore[attr-defined]
                self._handle_detection(result.face_count)
            except Exception:
                pass

    def _handle_detection(self, count: int) -> None:
        now = time.monotonic()
        with self._lock:
            changed = count != self._last_count
            cooldown_elapsed = self._last_count == -1 or (now - self._last_speak_time) >= self._cooldown
            should_speak = changed and cooldown_elapsed
            if should_speak:
                self._last_speak_time = now
            self._last_count = count
            message = self._build_message(count) if should_speak else None

        if message:
            try:
                self._tts.speak(message)  # type: ignore[attr-defined]
            except Exception:
                pass

    @staticmethod
    def _build_message(count: int) -> str:
        if count <= 0:
            return "前方无人"
        if count == 1:
            return "前方检测到一人"
        return f"前方检测到{count}人"