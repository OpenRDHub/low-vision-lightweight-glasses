"""RapidOCR 引擎适配器。

基于 PaddleOCR PP-OCRv4 的 ONNX 轻量化移植，仅依赖 onnxruntime，
无需 paddlepaddle/torch，CPU 推理速度快，适合实时助视场景。
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


class RapidOcrEngine:
    """RapidOCR 引擎适配器。

    warmup_async 预加载 ONNX 模型，recognize_async 执行检测→识别→坐标映射。
    confidence 为模型真实值或 None。
    """

    _MODEL_ID = "pp-ocr-v4-onnx"
    _MODEL_VERSION = "1.2.3"

    def __init__(
        self,
        lang: str = "ch",
        use_gpu: bool = False,
    ) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._ocr = None
        self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def get_info(self) -> OcrEngineInfo:
        return OcrEngineInfo(
            runtime="rapidocr",
            model_id=self._MODEL_ID,
            model_version=self._MODEL_VERSION,
            supported_languages=("zh", "en"),
            resource_version="onnx-bundled",
            license="Apache-2.0",
        )

    async def warmup_async(self, cancel_token: object | None = None) -> None:
        self.warmup()

    def warmup(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR

            self._ocr = RapidOCR()
            self._ready = True
        except Exception as e:
            raise ModelLoadError(f"RapidOCR 模型加载失败: {e}") from e

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
                model_id=self._MODEL_ID,
                model_version=self._MODEL_VERSION,
            )

        result, _elapse = self._ocr(img)

        blocks: list[OcrBlock] = []
        if result:
            for line_info in result:
                box, text, score = line_info

                if not text or not text.strip():
                    continue

                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                x = int(min(xs)) + roi_offset_x
                y = int(min(ys)) + roi_offset_y
                w = int(max(xs) - min(xs))
                h = int(max(ys) - min(ys))

                confidence: float | None
                try:
                    confidence = float(score)
                except (TypeError, ValueError):
                    confidence = None

                block = OcrBlock(
                    block_id=str(uuid.uuid4()),
                    text=text,
                    source_rect=ImageRect(x, y, w, h),
                    confidence=confidence,
                    model_id=self._MODEL_ID,
                    model_version=self._MODEL_VERSION,
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
            model_id=self._MODEL_ID,
            model_version=self._MODEL_VERSION,
        )