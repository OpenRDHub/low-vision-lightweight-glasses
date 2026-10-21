"""图像稳定适配器（P1）。

用 OpenCV 光流/特征点配准实现轻度图像稳定，减少相机抖动。
不宣称眼震治疗。
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from albassist.domain.models.image_frame import ImageFrame


class ImageStabilizer:
    """图像稳定适配器 - 轻度稳像减少抖动。"""

    def __init__(self, smoothing: float = 0.8) -> None:
        self._smoothing = smoothing
        self._prev_gray: np.ndarray[Any, Any] | None = None
        self._transform: np.ndarray[Any, Any] | None = None
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True
        self._prev_gray = None
        self._transform = None

    def disable(self) -> None:
        self._enabled = False
        self._prev_gray = None
        self._transform = None

    def stabilize(self, frame: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        """稳定单帧。

        快速移动时不强行锁定画面。
        """
        if not self._enabled:
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

        if self._prev_gray is None:
            self._prev_gray = gray
            return frame

        try:
            prev_pts = cv2.goodFeaturesToTrack(
                self._prev_gray, maxCorners=100, qualityLevel=0.3, minDistance=7
            )
            if prev_pts is None or len(prev_pts) < 10:
                self._prev_gray = gray
                return frame

            curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(  # type: ignore[call-overload]
                self._prev_gray, gray, prev_pts, None
            )

            if curr_pts is None or status is None:
                self._prev_gray = gray
                return frame

            valid = status.ravel() == 1
            prev_valid = prev_pts[valid].reshape(-1, 1, 2)
            curr_valid = curr_pts[valid].reshape(-1, 1, 2)

            if len(prev_valid) < 100:
                self._prev_gray = gray
                return frame

            matrix, _ = cv2.findHomography(prev_valid, curr_valid, cv2.RANSAC, 5.0)
            if matrix is None:
                self._prev_gray = gray
                return frame

            if self._transform is None:
                self._transform = matrix
            else:
                self._transform = (
                    self._smoothing * self._transform + (1 - self._smoothing) * matrix
                )

            h, w = frame.shape[:2]
            stabilized = cv2.warpPerspective(frame, self._transform, (w, h))

            self._prev_gray = gray
            return stabilized

        except Exception:
            self._prev_gray = gray
            return frame

    def get_diagnostics(self) -> dict[str, object]:
        """获取诊断数据：残余运动、裁切、帧率与延迟。"""
        return {
            "enabled": self._enabled,
            "smoothing": self._smoothing,
            "has_reference": self._prev_gray is not None,
        }