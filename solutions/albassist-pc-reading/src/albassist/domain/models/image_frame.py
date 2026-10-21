"""图像帧模型（不可变）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


from albassist.domain.exceptions import ImageFrameValidationError


@dataclass(frozen=True)
class ImageFrame:
    """图像帧 - 冻结后的不可变快照。

    所有视觉处理在副本上执行，原始冻结帧不得被修改。
    """

    frame_id: str
    width: int
    height: int
    stride: int
    pixel_format: str
    pixels: bytes
    captured_at: datetime

    def validate(self) -> None:
        """校验帧数据完整性。

        Raises:
            ImageFrameValidationError: 校验失败时。
        """
        if not self.frame_id or not self.frame_id.strip():
            raise ImageFrameValidationError("frame_id 不能为空")

        if self.width <= 0:
            raise ImageFrameValidationError(f"width 必须为正整数，得到 {self.width}")

        if self.height <= 0:
            raise ImageFrameValidationError(f"height 必须为正整数，得到 {self.height}")

        if self.stride <= 0:
            raise ImageFrameValidationError(f"stride 必须为正整数，得到 {self.stride}")

        if not self.pixel_format or not self.pixel_format.strip():
            raise ImageFrameValidationError("pixel_format 不能为空")

        bytes_per_pixel = {
            "RGB24": 3,
            "BGR24": 3,
            "RGBA32": 4,
            "BGRA32": 4,
            "GRAY8": 1,
            "GREY8": 1,
        }.get(self.pixel_format.upper())
        if bytes_per_pixel is None:
            raise ImageFrameValidationError(f"不支持的 pixel_format: {self.pixel_format}")
        minimum_stride = self.width * bytes_per_pixel
        if self.stride < minimum_stride:
            raise ImageFrameValidationError(
                f"stride {self.stride} 小于单行像素所需长度 {minimum_stride}"
            )

        min_pixels = self.stride * self.height
        if len(self.pixels) < min_pixels:
            raise ImageFrameValidationError(
                f"像素缓冲长度 {len(self.pixels)} 小于最小要求 {min_pixels} "
                f"(stride={self.stride} × height={self.height})"
            )

    @property
    def channels(self) -> int:
        """根据 pixel_format 推断通道数。"""
        fmt = self.pixel_format.upper()
        if "RGBA" in fmt or "BGRA" in fmt:
            return 4
        if "RGB" in fmt or "BGR" in fmt:
            return 3
        if "GRAY" in fmt or "GREY" in fmt:
            return 1
        return 0

    @staticmethod
    def now_utc() -> datetime:
        """当前 UTC 时间。"""
        return datetime.now(timezone.utc)