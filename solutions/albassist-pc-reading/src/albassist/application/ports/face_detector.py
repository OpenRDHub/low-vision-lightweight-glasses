"""人脸检测引擎端口（P2 差异化）。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from albassist.domain.models.face_models import FaceDetectionResult
from albassist.domain.models.image_frame import ImageFrame


@runtime_checkable
class IFaceDetector(Protocol):
    """离线人脸检测引擎端口。"""

    @property
    def is_ready(self) -> bool: ...

    async def warmup_async(self, cancel_token: object | None = None) -> None: ...

    async def detect_async(
        self,
        frame: ImageFrame,
        cancel_token: object | None = None,
    ) -> FaceDetectionResult: ...