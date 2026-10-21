"""OCR 推理线程 - 后台 QThread 执行识别。"""

from __future__ import annotations

import threading
from typing import Callable

from albassist.application.ports.ocr_engine import IOcrEngine
from albassist.domain.models.ocr_models import OcrResult, RecognitionRequest, SessionIdentity
from albassist.infrastructure.threading.cancel_token import CancellationToken
from albassist.infrastructure.threading.ocr_queue import OcrRequestQueue


class OcrWorker:
    """OCR 推理工作器 - 后台线程执行。

    从队列取请求调用 IOcrEngine.recognize_async，
    完成后通过回调投递主线程，校验四元组过期则丢弃。
    """

    def __init__(
        self,
        engine: IOcrEngine,
        on_result: Callable[[OcrResult], None],
        on_error: Callable[[str], None],
    ) -> None:
        self._engine = engine
        self._on_result = on_result
        self._on_error = on_error
        self._queue: OcrRequestQueue[tuple[RecognitionRequest, CancellationToken]] = OcrRequestQueue(capacity=2)
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def queue_size(self) -> int:
        return self._queue.size

    @property
    def dropped_count(self) -> int:
        return self._queue.dropped_count

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._work_loop, daemon=True, name="ocr-worker")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._queue.clear()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None

    def submit(
        self,
        request: RecognitionRequest,
        cancel_token: CancellationToken,
    ) -> None:
        """提交识别请求到队列。"""
        self._queue.put((request, cancel_token))

    def cancel_pending(self) -> None:
        """取消队列中待处理请求。"""
        self._queue.clear()

    def _work_loop(self) -> None:
        """推理工作循环（后台线程）。"""
        while self._running:
            item = self._queue.take(timeout=0.5)
            if item is None:
                continue

            request, cancel_token = item
            if cancel_token.is_cancelled:
                continue

            try:
                result = self._engine.recognize(request)  # type: ignore[attr-defined]
                if not cancel_token.is_cancelled:
                    self._on_result(result)
            except Exception as e:
                if not cancel_token.is_cancelled:
                    self._on_error(str(e))