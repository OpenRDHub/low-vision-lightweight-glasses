"""图片导入端口。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from albassist.domain.models.image_frame import ImageFrame


@runtime_checkable
class IImageImporter(Protocol):
    """图片导入端口。"""

    async def load_async(
        self,
        path: str,
        cancel_token: object | None = None,
    ) -> ImageFrame: ...