"""OpenCV 图像处理适配器。

所有操作在副本上执行，原图不可变。
"""

from __future__ import annotations

import uuid
from typing import Any

import cv2
import numpy as np

from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.visual_config import VisualConfig, VisualMode
from albassist.vision.frame_utils import frame_to_rgb


class OpenCvImageProcessor:
    """OpenCV 图像处理适配器。

    实现：缩放（1—8×）、灰度、黑白反色、对比度调整。
    P1：二值化、局部对比度增强、边缘显示。
    """

    async def apply_async(
        self,
        source: ImageFrame,
        config: VisualConfig,
        cancel_token: object | None = None,
    ) -> ImageFrame:
        """在副本上应用视觉配置。

        source.pixels 不被修改。
        """
        arr = self._to_numpy(source)
        processed = arr.copy()

        processed = self._apply_mode(processed, config)
        processed = self._apply_zoom(processed, config)

        return self._to_frame(processed, source.frame_id)

    def _apply_mode(self, img: np.ndarray[Any, Any], config: VisualConfig) -> np.ndarray[Any, Any]:
        mode = config.visual_mode

        if mode == VisualMode.ORIGINAL:
            return img

        if mode == VisualMode.GRAYSCALE:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        if mode == VisualMode.INVERT:
            return cv2.bitwise_not(img)

        if mode == VisualMode.CONTRAST:
            return self._apply_contrast(img, config.contrast_level)

        if mode == VisualMode.BINARIZE:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(
                gray, config.binarize_threshold, 255, cv2.THRESH_BINARY
            )
            return cv2.cvtColor(binary, cv2.COLOR_GRAY2RGB)

        if mode == VisualMode.LOCAL_CONTRAST:
            return self._apply_clahe(img)

        if mode == VisualMode.EDGE:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

        if mode == VisualMode.NIGHT:
            return self._apply_night(img)

        return img

    def _apply_night(self, img: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        """夜间增强（非生成式）：Gamma 提亮 + CLAHE 局部对比度。

        只做亮度/对比度映射，不生成或补全内容；
        原图保留，用户可随时切回原色核对。
        """
        # Gamma < 1 提亮暗部
        gamma = 0.45
        lookup = np.array(
            [((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8
        )
        brightened = cv2.LUT(img, lookup)

        # CLAHE 在亮度通道上增强局部对比度
        lab = cv2.cvtColor(brightened, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

    def _apply_contrast(self, img: np.ndarray[Any, Any], level: float) -> np.ndarray[Any, Any]:
        """调整对比度。"""
        adjusted = np.clip(img.astype(np.float32) * level, 0, 255)
        return adjusted.astype(np.uint8)

    def _apply_clahe(self, img: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        """CLAHE 局部对比度增强。"""
        lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)

    def _apply_zoom(self, img: np.ndarray[Any, Any], config: VisualConfig) -> np.ndarray[Any, Any]:
        """数字缩放（仅显示缩放）。"""
        zoom = config.zoom_factor
        if zoom == 1.0:
            return img

        height, width = img.shape[:2]
        new_width = int(width * zoom)
        new_height = int(height * zoom)
        return cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

    def _to_numpy(self, frame: ImageFrame) -> np.ndarray[Any, Any]:
        """ImageFrame → RGB numpy 数组。"""
        return frame_to_rgb(frame)

    def _to_frame(self, arr: np.ndarray[Any, Any], source_frame_id: str) -> ImageFrame:
        """numpy 数组 → ImageFrame。"""
        height, width = arr.shape[:2]
        return ImageFrame(
            frame_id=f"{source_frame_id}_processed",
            width=width,
            height=height,
            stride=width * 3,
            pixel_format="RGB24",
            pixels=arr.tobytes(),
            captured_at=ImageFrame.now_utc(),
        )