"""OpenCV 图片导入适配器。

用 cv2.imread 解码 PNG/JPEG 转为统一 RGB24 的 ImageFrame。
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from albassist.domain.exceptions import ImageDecodeError, UnsupportedImageFormatError
from albassist.domain.models.image_frame import ImageFrame


_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}


class OpenCvImageImporter:
    """OpenCV 图片导入适配器。"""

    async def load_async(
        self,
        path: str,
        cancel_token: object | None = None,
    ) -> ImageFrame:
        """从文件路径加载图片。

        Args:
            path: 图片文件路径。
            cancel_token: 取消令牌。

        Returns:
            ImageFrame: RGB24 格式的图像帧。

        Raises:
            UnsupportedImageFormatError: 不支持的格式。
            ImageDecodeError: 解码失败。
        """
        p = Path(path)
        if not p.exists():
            raise ImageDecodeError(f"文件不存在: {path}")

        ext = p.suffix.lower()
        if ext not in _SUPPORTED_EXTENSIONS:
            raise UnsupportedImageFormatError(
                f"不支持的图片格式: {ext}，支持: {_SUPPORTED_EXTENSIONS}"
            )

        raw = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if raw is None:
            raise ImageDecodeError(f"图片解码失败: {path}")

        rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        stride = width * 3
        pixels = rgb.tobytes()

        frame = ImageFrame(
            frame_id=str(uuid.uuid4()),
            width=width,
            height=height,
            stride=stride,
            pixel_format="RGB24",
            pixels=pixels,
            captured_at=ImageFrame.now_utc(),
        )
        frame.validate()
        return frame

    @staticmethod
    def from_numpy_array(arr: np.ndarray[Any, Any], frame_id: str | None = None) -> ImageFrame:
        """从 numpy 数组创建 ImageFrame（BGR → RGB）。"""
        if arr is None or arr.size == 0:
            raise ImageDecodeError("空数组")

        if len(arr.shape) == 2:
            rgb = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
        elif arr.shape[2] == 4:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGB)
        else:
            rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)

        height, width = rgb.shape[:2]
        return ImageFrame(
            frame_id=frame_id or str(uuid.uuid4()),
            width=width,
            height=height,
            stride=width * 3,
            pixel_format="RGB24",
            pixels=rgb.tobytes(),
            captured_at=ImageFrame.now_utc(),
        )