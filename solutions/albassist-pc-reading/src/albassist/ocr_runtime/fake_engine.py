"""Fake OCR 引擎 - 用于测试与 M0 未通过时占位。

返回固定结果，不调用真实模型。
"""

from __future__ import annotations

import uuid

from albassist.domain.geometry import ImageRect
from albassist.domain.models.ocr_models import (
    OcrBlock,
    OcrEngineInfo,
    OcrResult,
    RecognitionRequest,
)


class FakeOcrEngine:
    """Fake OCR 引擎 - 返回固定测试结果。"""

    def __init__(self, fake_text: str = "这是测试识别结果。This is test OCR result.") -> None:
        self._fake_text = fake_text
        self._ready = True

    @property
    def is_ready(self) -> bool:
        return self._ready

    def get_info(self) -> OcrEngineInfo:
        return OcrEngineInfo(
            runtime="fake",
            model_id="fake-model",
            model_version="0.0.1",
            supported_languages=("zh", "en"),
            resource_version="test",
            license="MIT",
        )

    async def warmup_async(self, cancel_token: object | None = None) -> None:
        self.warmup()

    def warmup(self) -> None:
        self._ready = True

    async def recognize_async(
        self,
        request: RecognitionRequest,
        cancel_token: object | None = None,
    ) -> OcrResult:
        return self.recognize(request)

    def recognize(self, request: RecognitionRequest) -> OcrResult:
        import time

        time.sleep(0.3)

        roi = request.region_of_interest
        w = max(roi.width, 1)
        h = max(roi.height, 1)

        num_lines = max(1, min(h // 30, 5))
        sample_texts = [
            "白化病低视力学生阅读辅助系统",
            "AI 助视学习软件 - 大字阅读版",
            "选中文字可转换为可调字号的大字",
            "按方向键切换上一段下一段",
            "识别结果未核对，请回查原图",
        ]

        blocks: list[OcrBlock] = []
        line_h = h // num_lines
        for i in range(num_lines):
            text = sample_texts[i % len(sample_texts)]
            block = OcrBlock(
                block_id=str(uuid.uuid4()),
                text=text,
                source_rect=ImageRect(roi.x, roi.y + i * line_h, w, line_h),
                confidence=0.88 + 0.05 * (1 - i / num_lines),
                model_id="fake-model",
                model_version="0.0.1",
                flags=("fake",),
            )
            blocks.append(block)

        return OcrResult(
            session_id=request.session_id,
            request_id=request.request_id,
            frame_id=request.frame_id,
            frame_revision=request.frame_revision,
            blocks=tuple(blocks),
            inference_time_ms=300.0,
            model_id="fake-model",
            model_version="0.0.1",
        )

    def set_ready(self, ready: bool) -> None:
        self._ready = ready