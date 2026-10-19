"""PaddleOCR 引擎适配器。

M0 验证后选定。检测→裁切→识别→坐标映射回原图。
"""

from __future__ import annotations

import time
import uuid

from albassist.domain.exceptions import ModelLoadError, OcrEngineNotReadyError
from albassist.domain.geometry import ImageRect
from albassist.domain.models.ocr_models import (
    OcrBlock,
    OcrEngineInfo,
    OcrResult,
    RecognitionRequest,
)
from albassist.vision.frame_utils import frame_to_rgb


class PaddleOcrEngine:
    """PaddleOCR 引擎适配器。

    warmup_async 预加载模型，recognize_async 执行检测→识别→坐标映射。
    confidence 为模型真实值或 None。
    """

    def __init__(
        self,
        model_dir: str = "models",
        use_gpu: bool = False,
        lang: str = "ch",
    ) -> None:
        self._model_dir = model_dir
        self._use_gpu = use_gpu
        self._lang = lang
        self._ocr = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def get_info(self) -> OcrEngineInfo:
        return OcrEngineInfo(
            runtime="paddleocr",
            model_id="paddle-ocr-v4",
            model_version="4.0.0",
            supported_languages=("zh", "en"),
            resource_version=self._model_dir,
            license="Apache-2.0",
        )

    async def warmup_async(self, cancel_token: object | None = None) -> None:
        try:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self._lang,
                use_gpu=self._use_gpu,
                show_log=False,
            )
            self._ready = True
        except Exception as e:
            raise ModelLoadError(f"PaddleOCR 模型加载失败: {e}") from e

    async def recognize_async(
        self,
        request: RecognitionRequest,
        cancel_token: object | None = None,
    ) -> OcrResult:
        if not self._ready or self._ocr is None:
            raise OcrEngineNotReadyError("OCR 引擎未就绪，请先调用 warmup_async")

        start_time = time.perf_counter()
        img = frame_to_rgb(request.image)

        roi = request.region_of_interest.clamp_to(request.image.width, request.image.height)
        roi_offset_x, roi_offset_y = roi.x, roi.y
        if not roi.is_empty:
            img = img[roi.y : roi.bottom, roi.x : roi.right]

        if img.shape[0] == 0 or img.shape[1] == 0:
            return OcrResult(
                session_id=request.session_id,
                request_id=request.request_id,
                frame_id=request.frame_id,
                frame_revision=request.frame_revision,
                blocks=(),
                inference_time_ms=0.0,
                model_id="paddle-ocr-v4",
                model_version="4.0.0",
            )

        result = self._ocr.ocr(img, cls=True)

        blocks: list[OcrBlock] = []
        if result and result[0]:
            for line_info in result[0]:
                box, (text, confidence) = line_info

                if not text or not text.strip():
                    continue

                xs = [int(p[0]) for p in box]
                ys = [int(p[1]) for p in box]
                x = min(xs) + roi_offset_x
                y = min(ys) + roi_offset_y
                w = max(xs) - min(xs)
                h = max(ys) - min(ys)

                block = OcrBlock(
                    block_id=str(uuid.uuid4()),
                    text=text,
                    source_rect=ImageRect(x, y, w, h),
                    confidence=float(confidence) if confidence is not None else None,
                    model_id="paddle-ocr-v4",
                    model_version="4.0.0",
                )
                blocks.append(block)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return OcrResult(
            session_id=request.session_id,
            request_id=request.request_id,
            frame_id=request.frame_id,
            frame_revision=request.frame_revision,
            blocks=tuple(blocks),
            inference_time_ms=elapsed_ms,
            model_id="paddle-ocr-v4",
            model_version="4.0.0",
        )