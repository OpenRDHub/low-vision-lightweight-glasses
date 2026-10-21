"""TextReflow 文字重排测试。"""

from __future__ import annotations

from albassist.application.text_reflow import TextReflow
from albassist.domain.geometry import ImageRect
from albassist.domain.models.ocr_models import OcrBlock


def _make_block(text: str, block_id: str = "b1") -> OcrBlock:
    return OcrBlock(
        block_id=block_id,
        text=text,
        source_rect=ImageRect(0, 0, 100, 50),
        confidence=0.9,
        model_id="test",
        model_version="1.0",
    )


class TestTextReflow:
    def test_empty_blocks(self) -> None:
        result = TextReflow.reflow([], 800, 48)
        assert result.lines == ()
        assert result.total_chars == 0

    def test_chinese_text(self) -> None:
        block = _make_block("这是一段中文测试文字")
        result = TextReflow.reflow([block], 200, 48)
        assert result.total_chars == 10
        assert len(result.lines) >= 1
        assert all(line.text for line in result.lines)

    def test_english_text(self) -> None:
        block = _make_block("This is a test English sentence for reflow.")
        result = TextReflow.reflow([block], 300, 48)
        assert result.total_chars > 0
        assert len(result.lines) >= 1

    def test_mixed_text(self) -> None:
        block = _make_block("这是Chinese and English混排test文字。")
        result = TextReflow.reflow([block], 400, 48)
        assert result.total_chars > 0
        assert len(result.lines) >= 1

    def test_text_not_modified(self) -> None:
        original = "这是测试文字Hello World"
        block = _make_block(original)
        result = TextReflow.reflow([block], 10000, 48)
        reflowed = "".join(line.text for line in result.lines)
        assert reflowed == original

    def test_multiple_blocks(self) -> None:
        blocks = [
            _make_block("第一段", "b1"),
            _make_block("第二段", "b2"),
            _make_block("第三段", "b3"),
        ]
        result = TextReflow.reflow(blocks, 800, 48)
        assert result.total_chars == 9
        block_indices = {line.block_index for line in result.lines}
        assert block_indices == {0, 1, 2}

    def test_zero_view_width(self) -> None:
        block = _make_block("测试")
        result = TextReflow.reflow([block], 0, 48)
        assert result.lines == ()

    def test_long_text_wraps(self) -> None:
        block = _make_block("这" * 100)
        result = TextReflow.reflow([block], 100, 48)
        assert len(result.lines) > 1