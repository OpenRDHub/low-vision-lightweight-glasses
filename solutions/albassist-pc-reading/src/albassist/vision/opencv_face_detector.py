"""OpenCV Haar 级联人脸检测适配器（P2）。

适配器优先使用 OpenCV 发行包附带的 Haar 模型。若当前 OpenCV 构建不含
``CascadeClassifier`` 或模型文件缺失，则明确保持未就绪，不伪造检测结果；
后续可在不改变 IFaceDetector 端口的前提下替换为 YuNet/DNN 适配器。
"""

from __future__ import annotations

import time

from albassist.domain.models.face_models import FaceBox, FaceDetectionResult
from albassist.domain.models.image_frame import ImageFrame
from albassist.vision.frame_utils import frame_to_gray


class OpenCvFaceDetector:
    """Haar 级联人脸检测适配器。"""

    _MODEL_ID = "haar-frontalface"
    _MODEL_VERSION = "1.0"

    def __init__(self, min_neighbors: int = 5, min_size: tuple[int, int] = (60, 60)) -> None:
        self._min_neighbors = min_neighbors
        self._min_size = min_size
        self._cascade: object | None = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def warmup_async(self, cancel_token: object | None = None) -> None:
        import cv2

        self._cascade = None
        self._ready = False
        cascade_type = getattr(cv2, "CascadeClassifier", None)
        data = getattr(cv2, "data", None)
        cascade_dir = getattr(data, "haarcascades", None)
        if cascade_type is None or not cascade_dir:
            return
        cascade_path = cascade_dir + "haarcascade_frontalface_default.xml"
        cascade = cascade_type(cascade_path)
        self._cascade = cascade
        self._ready = not cascade.empty()

    async def detect_async(
        self,
        frame: ImageFrame,
        cancel_token: object | None = None,
    ) -> FaceDetectionResult:
        if not self._ready or self._cascade is None:
            raise RuntimeError("人脸检测器未就绪，请先调用 warmup_async")

        import cv2

        start_time = time.perf_counter()
        gray = frame_to_gray(frame)
        gray = cv2.equalizeHist(gray)
        assert self._cascade is not None
        rects = self._cascade.detectMultiScale(  # type: ignore[attr-defined]
            gray,
            scaleFactor=1.1,
            minNeighbors=self._min_neighbors,
            minSize=self._min_size,
        )

        faces: list[FaceBox] = []
        for x, y, w, h in rects:
            faces.append(FaceBox(int(x), int(y), int(w), int(h)))

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return FaceDetectionResult(
            frame_id=frame.frame_id,
            faces=tuple(faces),
            inference_time_ms=elapsed_ms,
            model_id=self._MODEL_ID,
            model_version=self._MODEL_VERSION,
        )