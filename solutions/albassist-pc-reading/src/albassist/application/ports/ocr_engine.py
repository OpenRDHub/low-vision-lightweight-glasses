"""应用端口 - 纯 Protocol 定义，无具体实现。

端口文件不 import 任何适配器/SDK。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.ocr_models import (
    OcrEngineInfo,
    OcrResult,
    RecognitionRequest,
)
from albassist.domain.models.visual_config import VisualConfig


@runtime_checkable
class IOcrEngine(Protocol):
    """OCR 引擎端口。"""

    @property
    def is_ready(self) -> bool: ...

    def get_info(self) -> OcrEngineInfo: ...

    async def warmup_async(self, cancel_token: object | None = None) -> None: ...

    async def recognize_async(
        self,
        request: RecognitionRequest,
        cancel_token: object | None = None,
    ) -> OcrResult: ...