"""大字阅读版视图 - 重排文字、字号/行距/配色调整、块导航。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

from albassist.application.text_reflow import ReflowLine, TextReflow
from albassist.domain.models.ocr_models import OcrBlock
from albassist.domain.models.visual_config import VisualConfig


class ReadingView(QWidget):
    """大字阅读版视图。"""

    view_original_requested = Signal()
    next_block_requested = Signal()
    prev_block_requested = Signal()
    font_size_changed = Signal(int)
    line_spacing_changed = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.StrongFocus)

        self._blocks: tuple[OcrBlock, ...] = ()
        self._config = VisualConfig()
        self._current_block = -1

        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self._btn_original = QPushButton("看原图 (O)")
        self._btn_original.setMinimumSize(120, 44)
        self._btn_prev = QPushButton("上一段 (←)")
        self._btn_prev.setMinimumSize(120, 44)
        self._btn_next = QPushButton("下一段 (→)")
        self._btn_next.setMinimumSize(120, 44)
        self._btn_font_inc = QPushButton("字号 +")
        self._btn_font_inc.setMinimumSize(80, 44)
        self._btn_font_dec = QPushButton("字号 -")
        self._btn_font_dec.setMinimumSize(80, 44)
        self._btn_spacing_inc = QPushButton("行距 +")
        self._btn_spacing_inc.setMinimumSize(80, 44)
        self._btn_spacing_dec = QPushButton("行距 -")
        self._btn_spacing_dec.setMinimumSize(80, 44)

        self._btn_original.clicked.connect(self.view_original_requested.emit)
        self._btn_prev.clicked.connect(self.prev_block_requested.emit)
        self._btn_next.clicked.connect(self.next_block_requested.emit)
        self._btn_font_inc.clicked.connect(lambda: self.font_size_changed.emit(self._config.font_size + 4))
        self._btn_font_dec.clicked.connect(lambda: self.font_size_changed.emit(self._config.font_size - 4))
        self._btn_spacing_inc.clicked.connect(lambda: self.line_spacing_changed.emit(round(self._config.line_spacing + 0.1, 1)))
        self._btn_spacing_dec.clicked.connect(lambda: self.line_spacing_changed.emit(round(self._config.line_spacing - 0.1, 1)))

        for btn in [self._btn_original, self._btn_prev, self._btn_next, self._btn_font_inc, self._btn_font_dec, self._btn_spacing_inc, self._btn_spacing_dec]:
            toolbar.addWidget(btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._unverified_label = QLabel("⚠ 识别结果，未核对")
        self._unverified_label.setProperty("role", "unverified")
        layout.addWidget(self._unverified_label)

        self._text_label = QLabel()
        self._text_label.setObjectName("reading_text")
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._text_label.setTextFormat(Qt.RichText)
        layout.addWidget(self._text_label, 1)

        self._block_info = QLabel()
        layout.addWidget(self._block_info)

    def set_blocks(self, blocks: list[OcrBlock]) -> None:
        self._blocks = tuple(blocks)
        self._update_display()

    def set_config(self, config: VisualConfig) -> None:
        self._config = config
        self._update_display()

    def set_current_block(self, index: int) -> None:
        self._current_block = index
        self._update_display()

    def _update_display(self) -> None:
        if not self._blocks:
            self._text_label.setText("<i>未检测到文字</i>")
            self._block_info.setText("")
            return

        result = TextReflow.reflow(
            self._blocks,
            self.width() - 40,
            self._config.font_size,
            self._config.line_spacing,
        )

        html_parts: list[str] = []
        for line in result.lines:
            text = line.text
            if line.block_index == self._current_block:
                html_parts.append(
                    f'<span style="background-color: #E6F2FF; border: 2px solid #0066CC;">{text}</span>'
                )
            else:
                html_parts.append(text)
            html_parts.append("<br>")

        self._text_label.setText("".join(html_parts))

        text_color = self._config.text_color
        background_color = self._config.background_color
        if self._config.eye_care:
            # 数字阅读层的护眼效果只调整显示配色，不改变 OCR 原文。
            text_color = "#332B20"
            background_color = "#FFF4D6"
        style = (
            f"font-size: {self._config.font_size}px; "
            f"color: {text_color}; "
            f"background-color: {background_color}; "
            f"line-height: {self._config.line_spacing};"
        )
        self._text_label.setStyleSheet(style)

        total = len(self._blocks)
        current = self._current_block + 1 if self._current_block >= 0 else 0
        self._block_info.setText(f"第 {current}/{total} 段 | 字号 {self._config.font_size}px | 行距 {self._config.line_spacing}")