"""OCR 与阅读文档模型（全部 frozen dataclass）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import NamedTuple

from albassist.domain.exceptions import OcrBlockValidationError
from albassist.domain.geometry import ImageRect
from albassist.domain.models.image_frame import ImageFrame


class SessionIdentity(NamedTuple):
    """会话四元标识 - 用于任务关联和过期校验。"""

    session_id: str
    request_id: str
    frame_id: str
    frame_revision: int


@dataclass(frozen=True)
class OcrBlock:
    """OCR 识别文字块。

    - confidence 为 None 表示模型不提供置信度（不得伪造）。
    - text 不得为空字符串（空块不输出）。
    - source_rect 必须映射到原图坐标系。
    """

    block_id: str
    text: str
    source_rect: ImageRect
    confidence: float | None
    model_id: str
    model_version: str
    flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.block_id or not self.block_id.strip():
            raise OcrBlockValidationError("block_id 不能为空")
        if not self.text or not self.text.strip():
            raise OcrBlockValidationError("block_id 的 text 不得为空字符串（空块不输出）")
        if not self.model_id:
            raise OcrBlockValidationError("model_id 不能为空")
        if not self.model_version:
            raise OcrBlockValidationError("model_version 不能为空")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise OcrBlockValidationError(
                f"confidence 必须在 [0.0, 1.0] 范围内，得到 {self.confidence}"
            )


@dataclass(frozen=True)
class OcrResult:
    """OCR 识别结果。

    session_id + request_id + frame_id + frame_revision 必须与提交请求一致才能被接受。
    """

    session_id: str
    request_id: str
    frame_id: str
    frame_revision: int
    blocks: tuple[OcrBlock, ...]
    inference_time_ms: float
    model_id: str
    model_version: str

    @property
    def identity(self) -> SessionIdentity:
        return SessionIdentity(self.session_id, self.request_id, self.frame_id, self.frame_revision)

    @property
    def block_count(self) -> int:
        return len(self.blocks)

    @property
    def full_text(self) -> str:
        """所有块文字拼接。"""
        return "".join(b.text for b in self.blocks)


@dataclass(frozen=True)
class RecognitionRequest:
    """识别请求。"""

    session_id: str
    request_id: str
    frame_id: str
    frame_revision: int
    region_of_interest: ImageRect
    image: ImageFrame
    language_profile: str = "zh"

    @property
    def identity(self) -> SessionIdentity:
        return SessionIdentity(self.session_id, self.request_id, self.frame_id, self.frame_revision)


@dataclass(frozen=True)
class ReadingDocument:
    """阅读文档 - OCR 结果构建的可重排阅读文档。

    is_verified 默认 False，不得由 OCR 引擎修改。
    """

    document_id: str
    session_id: str
    frame_id: str
    frame_revision: int
    blocks: tuple[OcrBlock, ...]
    created_at: datetime
    is_verified: bool = False

    @property
    def identity(self) -> SessionIdentity:
        return SessionIdentity(
            self.session_id, "", self.frame_id, self.frame_revision
        )


@dataclass(frozen=True)
class OcrEngineInfo:
    """OCR 引擎信息。"""

    runtime: str
    model_id: str
    model_version: str
    supported_languages: tuple[str, ...]
    resource_version: str
    license: str