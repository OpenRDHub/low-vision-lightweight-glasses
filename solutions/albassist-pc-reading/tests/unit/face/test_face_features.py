"""人脸识别功能测试。

含模型校验、Haar 检测器 warmup/检测（协程直驱绕过沙箱事件循环）、
提醒消息构建。async 节流/端到端测试在用户本机运行。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from albassist.domain.models.face_models import FaceBox, FaceDetectionResult
from albassist.domain.models.image_frame import ImageFrame
from albassist.infrastructure.threading.face_alert_worker import FaceAlertWorker
from albassist.vision.opencv_face_detector import OpenCvFaceDetector


def _run(coro):  # type: ignore[no-untyped-def]
    """驱动无 await 的协程到完成，返回其值。"""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def _white_frame(width: int = 320, height: int = 240) -> ImageFrame:
    return ImageFrame(
        frame_id="f",
        width=width,
        height=height,
        stride=width * 3,
        pixel_format="RGB24",
        pixels=b"\xff" * (width * 3 * height),
        captured_at=datetime.now(timezone.utc),
    )


def test_face_box_valid() -> None:
    box = FaceBox(10, 20, 100, 120, 0.9)
    assert box.x == 10 and box.width == 100
    assert box.confidence == 0.9


def test_face_box_rejects_non_positive_size() -> None:
    with pytest.raises(ValueError):
        FaceBox(0, 0, 0, 100)
    with pytest.raises(ValueError):
        FaceBox(0, 0, 100, 0)


def test_face_box_rejects_bad_confidence() -> None:
    with pytest.raises(ValueError):
        FaceBox(0, 0, 10, 10, 1.5)


def test_face_detection_result_count() -> None:
    result = FaceDetectionResult(
        frame_id="f",
        faces=(FaceBox(0, 0, 10, 10), FaceBox(20, 20, 30, 30)),
    )
    assert result.face_count == 2


def test_opencv_face_detector_warmup() -> None:
    detector = OpenCvFaceDetector()
    assert detector.is_ready is False
    _run(detector.warmup_async())
    # OpenCV 5 的部分发行包移除了 Haar API/模型；此时能力必须显式未就绪。
    try:
        import cv2
        haar_available = hasattr(cv2, "CascadeClassifier") and bool(
            getattr(getattr(cv2, "data", None), "haarcascades", "")
        )
    except ImportError:
        haar_available = False
    assert detector.is_ready is haar_available


def test_opencv_face_detector_detects_blank_as_zero_faces() -> None:
    detector = OpenCvFaceDetector()
    _run(detector.warmup_async())
    if not detector.is_ready:
        pytest.skip("当前 OpenCV 构建未提供 Haar 人脸模型")
    result = _run(detector.detect_async(_white_frame()))
    assert isinstance(result, FaceDetectionResult)
    assert result.face_count == 0
    assert result.frame_id == "f"
    assert result.inference_time_ms >= 0.0


def test_face_alert_build_message() -> None:
    assert FaceAlertWorker._build_message(0) == "前方无人"
    assert FaceAlertWorker._build_message(1) == "前方检测到一人"
    assert FaceAlertWorker._build_message(3) == "前方检测到3人"


def test_face_alert_worker_enable_disable() -> None:
    class _StubDetector:
        is_ready = True

        async def warmup_async(self, cancel_token: object | None = None) -> None:
            return None

        async def detect_async(self, frame, cancel_token: object | None = None):  # type: ignore[no-untyped-def]
            return FaceDetectionResult(frame_id=frame.frame_id)

    class _StubTts:
        is_ready = True

        async def speak_async(self, text: str, rate: float = 1.0, language: str = "zh", cancel_token: object | None = None) -> None:
            return None

        async def pause_async(self) -> None:
            return None

        async def stop_async(self) -> None:
            return None

    worker = FaceAlertWorker(_StubDetector(), _StubTts())  # type: ignore[arg-type]
    assert worker.is_enabled is False
    worker.set_enabled(True)
    assert worker.is_enabled is True
    worker.set_enabled(False)
    assert worker.is_enabled is False