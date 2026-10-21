"""RapidOcrEngine 测试。

含纯单元测试（mock 模型，验证解析/坐标/异常逻辑）与真实集成测试（端到端识别）。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from albassist.domain.exceptions import ModelLoadError, OcrEngineNotReadyError
from albassist.domain.geometry import ImageRect
from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.ocr_models import RecognitionRequest
from albassist.ocr_runtime.rapid_engine import RapidOcrEngine


def _make_frame(width: int = 100, height: int = 100, fmt: str = "RGB24") -> ImageFrame:
    channels = {"RGB24": 3, "BGR24": 3, "RGBA32": 4, "BGRA32": 4, "GRAY8": 1, "GREY8": 1}[fmt]
    stride = width * channels
    return ImageFrame(
        frame_id="f1",
        width=width,
        height=height,
        stride=stride,
        pixel_format=fmt,
        pixels=b"\x00" * (stride * height),
        captured_at=datetime.now(timezone.utc),
    )


def _make_request(roi: ImageRect | None = None) -> RecognitionRequest:
    return RecognitionRequest(
        session_id="s1",
        request_id="r1",
        frame_id="f1",
        frame_revision=1,
        region_of_interest=roi if roi is not None else ImageRect(0, 0, 0, 0),
        image=_make_frame(),
        language_profile="zh",
    )


class _FakeOcr:
    """模拟 RapidOCR 调用，返回固定结构以验证解析逻辑。"""

    def __init__(self, result: list, elapse: list | None = None) -> None:
        self._result = result
        self._elapse = elapse or [0.1, 0.01, 0.05]
        self.calls = 0

    def __call__(self, img):  # type: ignore[no-untyped-def]
        self.calls += 1
        return self._result, self._elapse


def test_get_info() -> None:
    engine = RapidOcrEngine()
    info = engine.get_info()
    assert info.runtime == "rapidocr"
    assert info.model_id == "pp-ocr-v4-onnx"
    assert info.model_version == "1.2.3"
    assert "zh" in info.supported_languages
    assert info.license == "Apache-2.0"


def test_initial_not_ready() -> None:
    engine = RapidOcrEngine()
    assert engine.is_ready is False


@pytest.mark.asyncio
async def test_recognize_before_warmup_raises() -> None:
    engine = RapidOcrEngine()
    with pytest.raises(OcrEngineNotReadyError):
        await engine.recognize_async(_make_request())


@pytest.mark.asyncio
async def test_warmup_success_sets_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rapidocr_onnxruntime.RapidOCR", lambda: _FakeOcr(result=[]))
    engine = RapidOcrEngine()
    await engine.warmup_async()
    assert engine.is_ready is True


@pytest.mark.asyncio
async def test_warmup_failure_raises_model_load_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom() -> None:
        raise RuntimeError("onnx load failed")

    monkeypatch.setattr("rapidocr_onnxruntime.RapidOCR", _boom)
    engine = RapidOcrEngine()
    with pytest.raises(ModelLoadError):
        await engine.warmup_async()


@pytest.mark.asyncio
async def test_recognize_parses_result_and_filters_empty_text() -> None:
    fake = _FakeOcr(
        result=[
            [[[10, 10], [50, 10], [50, 30], [10, 30]], "你好", "0.95"],
            [[[10, 40], [50, 40], [50, 60], [10, 60]], "   ", "0.50"],
        ]
    )
    engine = RapidOcrEngine()
    engine._ocr = fake
    engine._ready = True

    result = await engine.recognize_async(_make_request())

    assert result.model_id == "pp-ocr-v4-onnx"
    assert result.block_count == 1
    block = result.blocks[0]
    assert block.text == "你好"
    assert block.confidence == pytest.approx(0.95)
    assert block.source_rect.x == 10
    assert block.source_rect.y == 10
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_recognize_applies_roi_offset() -> None:
    fake = _FakeOcr(result=[[[[10, 10], [50, 10], [50, 30], [10, 30]], "OCR", "0.88"]])
    engine = RapidOcrEngine()
    engine._ocr = fake
    engine._ready = True

    roi = ImageRect(5, 7, 50, 50)
    result = await engine.recognize_async(_make_request(roi=roi))

    assert result.block_count == 1
    assert result.blocks[0].source_rect.x == 15
    assert result.blocks[0].source_rect.y == 17


@pytest.mark.asyncio
async def test_recognize_score_non_numeric_becomes_none() -> None:
    fake = _FakeOcr(result=[[[[10, 10], [50, 10], [50, 30], [10, 30]], "x", "nan-like"]])
    engine = RapidOcrEngine()
    engine._ocr = fake
    engine._ready = True

    result = await engine.recognize_async(_make_request())
    assert result.blocks[0].confidence is None


@pytest.mark.asyncio
async def test_recognize_empty_result_returns_no_blocks() -> None:
    fake = _FakeOcr(result=[])
    engine = RapidOcrEngine()
    engine._ocr = fake
    engine._ready = True

    result = await engine.recognize_async(_make_request())
    assert result.block_count == 0
    assert result.inference_time_ms >= 0.0


@pytest.mark.asyncio
async def test_real_recognize_end_to_end() -> None:
    """真实集成测试：加载模型并识别带文字图像，证明端到端可用。"""
    pytest.importorskip("rapidocr_onnxruntime")
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    pil_img = Image.new("RGB", (320, 80), "white")
    draw = ImageDraw.Draw(pil_img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((15, 15), "你好OCR 123", fill="black", font=font)
    arr = np.array(pil_img)

    h, w = arr.shape[:2]
    frame = ImageFrame(
        frame_id="real-1",
        width=w,
        height=h,
        stride=w * 3,
        pixel_format="RGB24",
        pixels=arr.tobytes(),
        captured_at=datetime.now(timezone.utc),
    )
    request = RecognitionRequest(
        session_id="s",
        request_id="r",
        frame_id="real-1",
        frame_revision=1,
        region_of_interest=ImageRect(0, 0, 0, 0),
        image=frame,
        language_profile="zh",
    )

    engine = RapidOcrEngine()
    await engine.warmup_async()
    assert engine.is_ready is True

    result = await engine.recognize_async(request)
    assert result.block_count >= 1
    full = result.full_text
    assert "123" in full or "OCR" in full or "你好" in full
    assert result.inference_time_ms > 0.0