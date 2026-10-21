"""OCR 模型测试。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from albassist.domain.exceptions import OcrBlockValidationError
from albassist.domain.geometry import ImageRect
from albassist.domain.models.ocr_models import OcrBlock, OcrResult, ReadingDocument


def _make_block(**overrides: object) -> OcrBlock:
    defaults: dict[str, object] = {
        "block_id": "block-1",
        "text": "测试文字",
        "source_rect": ImageRect(0, 0, 100, 50),
        "confidence": 0.95,
        "model_id": "test-model",
        "model_version": "1.0",
        "flags": (),
    }
    defaults.update(overrides)
    return OcrBlock(**defaults)  # type: ignore[arg-type]


class TestOcrBlock:
    def test_valid_block(self) -> None:
        block = _make_block()
        assert block.text == "测试文字"

    def test_empty_text(self) -> None:
        with pytest.raises(OcrBlockValidationError, match="text"):
            _make_block(text="")

    def test_whitespace_text(self) -> None:
        with pytest.raises(OcrBlockValidationError, match="text"):
            _make_block(text="   ")

    def test_none_confidence(self) -> None:
        block = _make_block(confidence=None)
        assert block.confidence is None

    def test_invalid_confidence(self) -> None:
        with pytest.raises(OcrBlockValidationError, match="confidence"):
            _make_block(confidence=1.5)
        with pytest.raises(OcrBlockValidationError, match="confidence"):
            _make_block(confidence=-0.1)

    def test_empty_model_id(self) -> None:
        with pytest.raises(OcrBlockValidationError, match="model_id"):
            _make_block(model_id="")


class TestOcrResult:
    def test_identity(self) -> None:
        result = OcrResult(
            session_id="s1",
            request_id="r1",
            frame_id="f1",
            frame_revision=1,
            blocks=(_make_block(),),
            inference_time_ms=100.0,
            model_id="test-model",
            model_version="1.0",
        )
        identity = result.identity
        assert identity.session_id == "s1"
        assert identity.request_id == "r1"
        assert identity.frame_id == "f1"
        assert identity.frame_revision == 1

    def test_block_count(self) -> None:
        result = OcrResult(
            session_id="s1",
            request_id="r1",
            frame_id="f1",
            frame_revision=1,
            blocks=(_make_block(), _make_block(block_id="block-2")),
            inference_time_ms=100.0,
            model_id="test-model",
            model_version="1.0",
        )
        assert result.block_count == 2

    def test_full_text(self) -> None:
        result = OcrResult(
            session_id="s1",
            request_id="r1",
            frame_id="f1",
            frame_revision=1,
            blocks=(_make_block(text="你好"), _make_block(text="世界", block_id="b2")),
            inference_time_ms=100.0,
            model_id="test-model",
            model_version="1.0",
        )
        assert result.full_text == "你好世界"


class TestReadingDocument:
    def test_default_is_verified_false(self) -> None:
        doc = ReadingDocument(
            document_id="d1",
            session_id="s1",
            frame_id="f1",
            frame_revision=1,
            blocks=(_make_block(),),
            created_at=datetime.now(timezone.utc),
        )
        assert doc.is_verified is False