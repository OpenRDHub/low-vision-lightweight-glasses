"""倾斜/透视校正适配器（P1）。

用 OpenCV 轮廓/霍夫直线检测纸面倾斜并透视变换校正。
保留原图可返回，不宣称对任意曲面课本有效。
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np


class DeskewCorrector:
    """倾斜校正适配器。"""

    def __init__(self) -> None:
        self._original: np.ndarray[Any, Any] | None = None

    def detect_and_correct(self, image: np.ndarray[Any, Any]) -> tuple[np.ndarray[Any, Any], float]:
        """检测倾斜角度并校正。

        Returns:
            (校正后图像, 倾斜角度)
        """
        self._original = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image

        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 100:
            return image, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 5:
            return image, angle

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        corrected = cv2.warpAffine(
            image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        return corrected, angle

    def restore_original(self) -> np.ndarray[Any, Any] | None:
        """恢复原始倾斜画面。"""
        return self._original

    def detect_perspective(self, image: np.ndarray[Any, Any]) -> np.ndarray[Any, Any] | None:
        """检测四角并进行透视校正。

        返回校正后图像或 None（未检测到四角时）。
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if len(image.shape) == 3 else image
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=cv2.contourArea)
        epsilon = 0.02 * cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, epsilon, True)

        if len(approx) != 4:
            return None

        pts = approx.reshape(4, 2).astype(np.float32)
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect

        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        dst = np.array(
            [
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, matrix, (max_width, max_height))

    @staticmethod
    def _order_points(pts: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect