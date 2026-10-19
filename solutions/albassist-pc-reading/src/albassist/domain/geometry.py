"""几何模型与坐标空间。

Domain 层不引用 cv2/numpy/PySide6 等任何外部 SDK。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CoordinateSpace(Enum):
    """坐标空间枚举。"""

    SOURCE_IMAGE = "source_image"
    ROI_LOCAL = "roi_local"
    VIEW_LOGICAL = "view_logical"


@dataclass(frozen=True)
class ImageRect:
    """图像矩形区域（不可变）。

    所有坐标值均为整数像素。clamp_to 使用 long 中间运算防溢出。
    """

    x: int
    y: int
    width: int
    height: int

    @property
    def is_empty(self) -> bool:
        """是否为空矩形。"""
        return self.width <= 0 or self.height <= 0

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        return self.width * self.height

    def clamp_to(self, image_width: int, image_height: int) -> ImageRect:
        """将矩形裁剪到图像边界内。

        使用 long 中间运算防溢出。
        """
        if image_width <= 0 or image_height <= 0:
            return ImageRect(0, 0, 0, 0)

        clamped_x = max(0, self.x)
        clamped_y = max(0, self.y)
        clamped_right = min(int(self.x) + int(self.width), image_width)
        clamped_bottom = min(int(self.y) + int(self.height), image_height)

        clamped_width = max(0, clamped_right - clamped_x)
        clamped_height = max(0, clamped_bottom - clamped_y)

        return ImageRect(clamped_x, clamped_y, clamped_width, clamped_height)

    def contains(self, other: ImageRect) -> bool:
        """是否包含另一个矩形。"""
        return (
            self.x <= other.x
            and self.y <= other.y
            and other.right <= self.right
            and other.bottom <= self.bottom
        )

    def intersects(self, other: ImageRect) -> bool:
        """是否与另一个矩形相交。"""
        return not (
            self.right <= other.x
            or other.right <= self.x
            or self.bottom <= other.y
            or other.bottom <= self.y
        )