"""人脸检测模型（全部 frozen dataclass）。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FaceBox:
    """人脸框 - 原图坐标系。"""

    x: int
    y: int
    width: int
    height: int
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"人脸框宽高必须为正，得到 {self.width}x{self.height}")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence 必须在 [0.0, 1.0]，得到 {self.confidence}")


@dataclass(frozen=True)
class FaceDetectionResult:
    """人脸检测结果。"""

    frame_id: str
    faces: tuple[FaceBox, ...] = field(default_factory=tuple)
    inference_time_ms: float = 0.0
    model_id: str = "haar-frontalface"
    model_version: str = "1.0"

    @property
    def face_count(self) -> int:
        return len(self.faces)