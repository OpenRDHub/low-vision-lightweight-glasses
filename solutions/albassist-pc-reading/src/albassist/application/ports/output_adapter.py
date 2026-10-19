"""输出适配端口与 RenderModel。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.ocr_models import OcrBlock
from albassist.domain.models.visual_config import VisualConfig


@dataclass(frozen=True)
class RenderModel:
    """视图无关的渲染模型。

    应用层只产生 RenderModel，不接触 QImage/QPixmap 等视图类型。
    """

    session_id: str
    original_frame: ImageFrame | None
    blocks: tuple[OcrBlock, ...]
    current_block_index: int
    visual_config: VisualConfig
    is_frozen: bool
    is_recognizing: bool
    status_message: str
    view_mode: str = "original"


@runtime_checkable
class IOutputAdapter(Protocol):
    """输出适配端口。"""

    async def render_async(
        self,
        model: RenderModel,
        cancel_token: object | None = None,
    ) -> None: ...