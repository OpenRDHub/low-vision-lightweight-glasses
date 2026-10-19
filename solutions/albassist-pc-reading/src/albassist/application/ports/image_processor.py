"""图像处理端口。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.visual_config import VisualConfig


@runtime_checkable
class IImageProcessor(Protocol):
    """图像处理端口 - 所有操作在副本上执行。"""

    async def apply_async(
        self,
        source: ImageFrame,
        config: VisualConfig,
        cancel_token: object | None = None,
    ) -> ImageFrame: ...