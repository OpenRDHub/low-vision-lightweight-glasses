"""视觉配置与模式模型。"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum

from albassist.domain.exceptions import VisualConfigValidationError


class VisualMode(Enum):
    """视觉模式枚举。

    P0: ORIGINAL / GRAYSCALE / INVERT / CONTRAST
    P1: BINARIZE / LOCAL_CONTRAST / EDGE / NIGHT
    """

    ORIGINAL = "original"
    GRAYSCALE = "grayscale"
    INVERT = "invert"
    CONTRAST = "contrast"
    BINARIZE = "binarize"
    LOCAL_CONTRAST = "local_contrast"
    EDGE = "edge"
    NIGHT = "night"


# 与产品 PRD 保持一致：数字显示缩放不是光学倍率，当前支持 1—8×。
_ZOOM_MIN, _ZOOM_MAX = 1.0, 8.0
_CONTRAST_MIN, _CONTRAST_MAX = 0.0, 2.0
_FONT_SIZE_MIN, _FONT_SIZE_MAX = 24, 96
_LINE_SPACING_MIN, _LINE_SPACING_MAX = 1.2, 2.0


@dataclass(frozen=True)
class VisualConfig:
    """视觉配置（不可变）。

    修改用 dataclasses.replace 产生新实例。
    """

    zoom_factor: float = 1.0
    visual_mode: VisualMode = VisualMode.ORIGINAL
    contrast_level: float = 1.0
    font_size: int = 48
    line_spacing: float = 1.5
    text_color: str = "#000000"
    background_color: str = "#FFFFFF"
    binarize_threshold: float = 127.5
    eye_care: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("zoom_factor", self.zoom_factor),
            ("contrast_level", self.contrast_level),
            ("line_spacing", self.line_spacing),
            ("binarize_threshold", self.binarize_threshold),
        ):
            if not math.isfinite(value):
                raise VisualConfigValidationError(f"{name} 必须是有限数值")
        if not (_ZOOM_MIN <= self.zoom_factor <= _ZOOM_MAX):
            raise VisualConfigValidationError(
                f"zoom_factor 必须在 [{_ZOOM_MIN}, {_ZOOM_MAX}] 范围内，得到 {self.zoom_factor}"
            )
        if not (_CONTRAST_MIN <= self.contrast_level <= _CONTRAST_MAX):
            raise VisualConfigValidationError(
                f"contrast_level 必须在 [{_CONTRAST_MIN}, {_CONTRAST_MAX}] 范围内，"
                f"得到 {self.contrast_level}"
            )
        if not (_FONT_SIZE_MIN <= self.font_size <= _FONT_SIZE_MAX):
            raise VisualConfigValidationError(
                f"font_size 必须在 [{_FONT_SIZE_MIN}, {_FONT_SIZE_MAX}] 范围内，"
                f"得到 {self.font_size}"
            )
        if not (_LINE_SPACING_MIN <= self.line_spacing <= _LINE_SPACING_MAX):
            raise VisualConfigValidationError(
                f"line_spacing 必须在 [{_LINE_SPACING_MIN}, {_LINE_SPACING_MAX}] 范围内，"
                f"得到 {self.line_spacing}"
            )
        if not (0.0 <= self.binarize_threshold <= 255.0):
            raise VisualConfigValidationError("binarize_threshold 必须在 [0, 255] 范围内")
        if not self.text_color.strip() or not self.background_color.strip():
            raise VisualConfigValidationError("文字和背景颜色不能为空")

    @staticmethod
    def reset() -> VisualConfig:
        """返回默认实例。"""
        return VisualConfig()

    def with_zoom(self, zoom: float) -> VisualConfig:
        return replace(self, zoom_factor=zoom)

    def with_mode(self, mode: VisualMode) -> VisualConfig:
        return replace(self, visual_mode=mode)

    def with_contrast(self, contrast: float) -> VisualConfig:
        return replace(self, contrast_level=contrast)

    def with_eye_care(self, enabled: bool) -> VisualConfig:
        return replace(self, eye_care=enabled)

    def with_font_size(self, size: int) -> VisualConfig:
        return replace(self, font_size=size)

    def with_line_spacing(self, spacing: float) -> VisualConfig:
        return replace(self, line_spacing=spacing)