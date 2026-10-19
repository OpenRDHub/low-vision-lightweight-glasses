"""ImageFrame ↔ numpy 共享转换工具。

消除各适配器（OCR/人脸/图像处理）中重复的像素格式转换逻辑。
Domain 不依赖本模块；仅 vision/ocr_runtime/infrastructure 适配器使用。
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from albassist.domain.models.image_frame import ImageFrame


def _packed(frame: ImageFrame) -> np.ndarray[Any, Any]:
    """ImageFrame → (H, W, C) numpy 数组，正确跳过行尾 padding。"""
    frame.validate()
    channels = frame.channels
    rows = np.frombuffer(frame.pixels, dtype=np.uint8).reshape(
        frame.height, frame.stride
    )
    return rows[:, : frame.width * channels].reshape(
        frame.height, frame.width, channels
    )


def frame_to_rgb(frame: ImageFrame) -> np.ndarray[Any, Any]:
    """ImageFrame → RGB numpy 数组。"""
    packed = _packed(frame)
    fmt = frame.pixel_format.upper()
    if fmt == "RGB24":
        return packed
    if fmt == "BGR24":
        return cv2.cvtColor(packed, cv2.COLOR_BGR2RGB)
    if fmt == "RGBA32":
        return cv2.cvtColor(packed, cv2.COLOR_RGBA2RGB)
    if fmt == "BGRA32":
        return cv2.cvtColor(packed, cv2.COLOR_BGRA2RGB)
    if fmt in {"GRAY8", "GREY8"}:
        return cv2.cvtColor(packed, cv2.COLOR_GRAY2RGB)
    raise ValueError(f"不支持的像素格式: {frame.pixel_format}")


def frame_to_gray(frame: ImageFrame) -> np.ndarray[Any, Any]:
    """ImageFrame → 单通道灰度 numpy 数组。"""
    packed = _packed(frame)
    fmt = frame.pixel_format.upper()
    if fmt in {"GRAY8", "GREY8"}:
        return packed[:, :, 0]
    if fmt == "RGB24":
        return cv2.cvtColor(packed, cv2.COLOR_RGB2GRAY)
    if fmt == "BGR24":
        return cv2.cvtColor(packed, cv2.COLOR_BGR2GRAY)
    if fmt == "RGBA32":
        return cv2.cvtColor(packed, cv2.COLOR_RGBA2GRAY)
    if fmt == "BGRA32":
        return cv2.cvtColor(packed, cv2.COLOR_BGRA2GRAY)
    raise ValueError(f"不支持的像素格式: {frame.pixel_format}")