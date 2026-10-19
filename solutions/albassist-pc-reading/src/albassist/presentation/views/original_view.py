"""原图视图 - 放大/缩小、选区、视觉模式、全局导航小窗。"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QMouseEvent, QPaintEvent, QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget

from albassist.domain.geometry import ImageRect
from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.visual_config import VisualConfig, VisualMode


_MAX_RENDER_PIXELS = 12_000_000


class OriginalView(QWidget):
    """原图视图 - 显示放大原图与选区。"""

    selection_changed = Signal(int, int, int, int)

    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)

        self._frame: ImageFrame | None = None
        self._config = VisualConfig()
        self._selection = ImageRect(0, 0, 0, 0)
        self._selecting = False
        self._select_start = (0, 0)
        self._offset = (0, 0)
        self._image_data: bytes | None = None
        self._frozen = False
        self._panning = False
        self._pan_start = (0, 0)
        self._highlight_rect: ImageRect | None = None
        self._pixmap_cache: tuple[tuple[Any, ...], QPixmap] | None = None

    def set_frame(self, frame: ImageFrame | None) -> None:
        if frame is not None:
            frame.validate()
        self._frame = frame
        self._selection = ImageRect(0, 0, 0, 0)
        self._highlight_rect = None
        self._image_data = None
        self._pixmap_cache = None
        self.update()

    def set_config(self, config: VisualConfig) -> None:
        self._config = config
        self.update()

    def set_frozen(self, frozen: bool) -> None:
        self._frozen = frozen
        if not frozen:
            self._offset = (0, 0)
            self._highlight_rect = None
        self.update()

    def set_highlight(self, rect: ImageRect | None) -> None:
        self._highlight_rect = rect
        self.update()

    def set_selection(self, rect: ImageRect) -> None:
        self._selection = rect
        self.update()

    def clear_selection(self) -> None:
        self._selection = ImageRect(0, 0, 0, 0)
        self.update()

    def get_selection(self) -> ImageRect:
        if self._selection.is_empty or self._frame is None:
            return self._selection

        total_scale = self._rendered_scale()
        if total_scale <= 0:
            return ImageRect(0, 0, 0, 0)

        img_w = max(int(self._frame.width * total_scale), 1)
        img_h = max(int(self._frame.height * total_scale), 1)
        img_x = (self.width() - img_w) // 2 + self._offset[0]
        img_y = (self.height() - img_h) // 2 + self._offset[1]

        x = int((self._selection.x - img_x) / total_scale)
        y = int((self._selection.y - img_y) / total_scale)
        w = int(self._selection.width / total_scale)
        h = int(self._selection.height / total_scale)

        return ImageRect(x, y, w, h).clamp_to(self._frame.width, self._frame.height)

    def reset_view(self) -> None:
        self._offset = (0, 0)
        self.update()

    def _rendered_scale(self) -> float:
        """返回图像被绘制时的实际缩放系数（含控件适配与内存上限）。"""
        if self._frame is None:
            return 0.0

        widget_w = max(self.width(), 1)
        widget_h = max(self.height(), 1)
        base_scale = min(widget_w / self._frame.width, widget_h / self._frame.height)
        scale = self._config.zoom_factor * base_scale

        max_scale = math.sqrt(_MAX_RENDER_PIXELS / (self._frame.width * self._frame.height))
        return min(scale, max_scale)

    def _to_pixmap(self) -> QPixmap | None:
        if self._frame is None:
            self._pixmap_cache = None
            return None

        widget_w = max(self.width(), 1)
        widget_h = max(self.height(), 1)
        scale = self._rendered_scale()
        cache_key = (
            self._frame.frame_id,
            self._config,
            round(scale, 4),
            widget_w,
            widget_h,
        )
        if self._pixmap_cache is not None and self._pixmap_cache[0] == cache_key:
            return self._pixmap_cache[1]

        new_w = max(int(self._frame.width * scale), 1)
        new_h = max(int(self._frame.height * scale), 1)

        try:
            arr = self._to_rgb_array(self._frame)

            if (new_w, new_h) != (self._frame.width, self._frame.height):
                import cv2
                interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
                arr = cv2.resize(arr, (new_w, new_h), interpolation=interpolation)

            mode = self._config.visual_mode
            if mode == VisualMode.GRAYSCALE:
                import cv2
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                arr = np.stack([gray, gray, gray], axis=2)
            elif mode == VisualMode.INVERT:
                arr = 255 - arr
            elif mode == VisualMode.CONTRAST:
                arr = np.clip(arr.astype(np.float32) * self._config.contrast_level, 0, 255).astype(np.uint8)
            elif mode == VisualMode.BINARIZE:
                import cv2
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                _, binary = cv2.threshold(gray, int(self._config.binarize_threshold), 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                arr = np.stack([binary, binary, binary], axis=2)
            elif mode == VisualMode.LOCAL_CONTRAST:
                import cv2
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                arr = np.stack([enhanced, enhanced, enhanced], axis=2)
            elif mode == VisualMode.EDGE:
                import cv2
                gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                edges = cv2.Canny(gray, 50, 150)
                arr = np.stack([edges, edges, edges], axis=2)

            if self._config.eye_care:
                arr = arr.copy()
                arr[:, :, 2] = np.clip(arr[:, :, 2].astype(np.float32) * 0.6, 0, 255).astype(np.uint8)

            h, w = arr.shape[:2]
            self._image_data = arr.tobytes()
            qimage = QImage(self._image_data, w, h, w * 3, QImage.Format_RGB888)
            if qimage.isNull():
                return None
            pixmap = QPixmap.fromImage(qimage)
        except Exception:
            self._pixmap_cache = None
            return None

        self._pixmap_cache = (cache_key, pixmap)
        return pixmap

    @staticmethod
    def _to_rgb_array(frame: ImageFrame) -> np.ndarray[Any, Any]:
        """将带 stride 的输入帧转换为 RGB 数组供显示。"""
        frame.validate()
        channels = frame.channels
        rows = np.frombuffer(frame.pixels, dtype=np.uint8).reshape(frame.height, frame.stride)
        packed = rows[:, : frame.width * channels].reshape(frame.height, frame.width, channels)
        fmt = frame.pixel_format.upper()
        if fmt == "RGB24":
            return packed
        import cv2
        if fmt == "BGR24":
            return cv2.cvtColor(packed, cv2.COLOR_BGR2RGB)
        if fmt == "RGBA32":
            return cv2.cvtColor(packed, cv2.COLOR_RGBA2RGB)
        if fmt == "BGRA32":
            return cv2.cvtColor(packed, cv2.COLOR_BGRA2RGB)
        if fmt in {"GRAY8", "GREY8"}:
            return cv2.cvtColor(packed, cv2.COLOR_GRAY2RGB)
        raise ValueError(f"不支持的像素格式: {frame.pixel_format}")

    def paintEvent(self, event: QPaintEvent) -> None:
        pixmap = self._to_pixmap()

        painter = QPainter(self)
        try:
            bg_color = QColor("#F5F5F5") if self._frozen else QColor("#FFFFFF")
            painter.fillRect(self.rect(), bg_color)

            if pixmap is not None:
                x = (self.width() - pixmap.width()) // 2 + self._offset[0]
                y = (self.height() - pixmap.height()) // 2 + self._offset[1]
                painter.drawPixmap(x, y, pixmap)

            if self._frozen:
                pen = QPen(QColor("#CC0000"), 4)
                painter.setPen(pen)
                painter.drawRect(2, 2, self.width() - 4, self.height() - 4)
                painter.setPen(QColor("#CC0000"))
                font = painter.font()
                font.setPointSize(14)
                font.setBold(True)
                painter.setFont(font)
                painter.drawText(10, 25, "已冻结 - 框选文字后按 R 识别")

            if not self._selection.is_empty:
                pen = QPen(QColor("#FF0000"), 2, Qt.DashLine)
                painter.setPen(pen)
                painter.drawRect(
                    self._selection.x + self._offset[0],
                    self._selection.y + self._offset[1],
                    self._selection.width,
                    self._selection.height,
                )

            if self._highlight_rect is not None and not self._highlight_rect.is_empty and self._frame is not None:
                total_scale = self._rendered_scale()
                img_w = max(int(self._frame.width * total_scale), 1)
                img_h = max(int(self._frame.height * total_scale), 1)
                hx = (self.width() - img_w) // 2 + self._offset[0]
                hy = (self.height() - img_h) // 2 + self._offset[1]
                pen = QPen(QColor("#0066CC"), 3)
                painter.setPen(pen)
                painter.setBrush(QColor(0, 102, 204, 40))
                painter.drawRect(
                    hx + int(self._highlight_rect.x * total_scale),
                    hy + int(self._highlight_rect.y * total_scale),
                    int(self._highlight_rect.width * total_scale),
                    int(self._highlight_rect.height * total_scale),
                )

            if self._config.zoom_factor > 2.0 and self._frame is not None:
                self._draw_minimap(painter)
        finally:
            painter.end()

    def _draw_minimap(self, painter: QPainter) -> None:
        """全局导航小窗。"""
        if self._frame is None:
            return

        mini_w, mini_h = 120, 90
        x = self.width() - mini_w - 10
        y = 10

        painter.setPen(QPen(QColor("#333333"), 2))
        painter.setBrush(QColor("#F0F0F0"))
        painter.drawRect(x, y, mini_w, mini_h)

        scale_x = mini_w / self._frame.width
        scale_y = mini_h / self._frame.height

        if not self._selection.is_empty:
            painter.setPen(QPen(QColor("#FF0000"), 2))
            painter.setBrush(QColor("#FF000030"))
            painter.drawRect(
                x + int(self._selection.x * scale_x),
                y + int(self._selection.y * scale_y),
                int(self._selection.width * scale_x),
                int(self._selection.height * scale_y),
            )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._selecting = True
            self._select_start = (int(event.position().x()), int(event.position().y()))
            self._selection = ImageRect(self._select_start[0], self._select_start[1], 0, 0)
        elif event.button() == Qt.RightButton:
            self._panning = True
            self._pan_start = (int(event.position().x()) - self._offset[0],
                               int(event.position().y()) - self._offset[1])

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting:
            x = min(self._select_start[0], int(event.position().x()))
            y = min(self._select_start[1], int(event.position().y()))
            w = abs(int(event.position().x()) - self._select_start[0])
            h = abs(int(event.position().y()) - self._select_start[1])
            self._selection = ImageRect(x, y, w, h)
            self.update()
        elif self._panning:
            self._offset = (int(event.position().x()) - self._pan_start[0],
                            int(event.position().y()) - self._pan_start[1])
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            if not self._selection.is_empty and self._frame is not None:
                # 信号统一发原图坐标；选框本身仍保留视图坐标用于绘制。
                source_rect = self.get_selection()
                self.selection_changed.emit(
                    source_rect.x, source_rect.y, source_rect.width, source_rect.height
                )
            self.update()
        elif event.button() == Qt.RightButton:
            self._panning = False