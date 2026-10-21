"""ImageFrame 模型测试。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from albassist.domain.exceptions import ImageFrameValidationError
from albassist.domain.models.image_frame import ImageFrame


def _make_frame(**overrides: object) -> ImageFrame:
    defaults: dict[str, object] = {
        "frame_id": "test-frame",
        "width": 100,
        "height": 100,
        "stride": 300,
        "pixel_format": "RGB24",
        "pixels": b"\x00" * (300 * 100),
        "captured_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return ImageFrame(**defaults)  # type: ignore[arg-type]


class TestImageFrame:
    def test_valid_frame(self) -> None:
        frame = _make_frame()
        frame.validate()

    def test_empty_frame_id(self) -> None:
        frame = _make_frame(frame_id="")
        with pytest.raises(ImageFrameValidationError, match="frame_id"):
            frame.validate()

    def test_zero_width(self) -> None:
        frame = _make_frame(width=0)
        with pytest.raises(ImageFrameValidationError, match="width"):
            frame.validate()

    def test_zero_height(self) -> None:
        frame = _make_frame(height=0)
        with pytest.raises(ImageFrameValidationError, match="height"):
            frame.validate()

    def test_zero_stride(self) -> None:
        frame = _make_frame(stride=0)
        with pytest.raises(ImageFrameValidationError, match="stride"):
            frame.validate()

    def test_empty_pixel_format(self) -> None:
        frame = _make_frame(pixel_format="")
        with pytest.raises(ImageFrameValidationError, match="pixel_format"):
            frame.validate()

    def test_insufficient_pixels(self) -> None:
        frame = _make_frame(pixels=b"\x00" * 100)
        with pytest.raises(ImageFrameValidationError, match="像素缓冲"):
            frame.validate()

    def test_unsupported_pixel_format(self) -> None:
        frame = _make_frame(pixel_format="YUV420")
        with pytest.raises(ImageFrameValidationError, match="不支持"):
            frame.validate()

    def test_stride_shorter_than_pixel_row(self) -> None:
        frame = _make_frame(stride=299, pixels=b"\x00" * (299 * 100))
        with pytest.raises(ImageFrameValidationError, match="stride"):
            frame.validate()

    def test_channels_rgb(self) -> None:
        frame = _make_frame()
        assert frame.channels == 3

    def test_frozen(self) -> None:
        frame = _make_frame()
        with pytest.raises(AttributeError):
            frame.width = 200  # type: ignore[misc]