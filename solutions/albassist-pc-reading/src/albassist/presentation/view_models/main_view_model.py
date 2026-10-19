"""ViewModel 协调层。

用 PySide6 Signal/Property，依赖注入端口不直接 new 具体类。
ViewModel 不 import QWidget/QMainWindow 视图类型。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, Signal

from albassist.application.ports.camera_source import CameraDevice
from albassist.application.session_manager import SessionManager, SessionState
from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.ocr_models import OcrBlock, OcrResult, ReadingDocument
from albassist.domain.models.visual_config import VisualConfig, VisualMode


class MainViewModel(QObject):
    """主 ViewModel - 协调子 VM 与会话状态。"""

    state_changed = Signal(str)
    status_message_changed = Signal(str)
    original_frame_changed = Signal(object)
    reading_document_changed = Signal(object)
    visual_config_changed = Signal(object)
    blocks_changed = Signal(list)
    current_block_changed = Signal(int)
    is_frozen_changed = Signal(bool)
    is_recognizing_changed = Signal(bool)
    error_occurred = Signal(str)
    info_message = Signal(str)
    import_image_requested = Signal(str)
    recognize_requested = Signal(object)
    cancel_requested = Signal()

    def __init__(self, session_manager: SessionManager) -> None:
        super().__init__()
        self._session = session_manager
        self._visual_config = VisualConfig()
        self._original_frame: ImageFrame | None = None
        self._reading_document: ReadingDocument | None = None
        self._blocks: tuple[OcrBlock, ...] = ()
        self._current_block_index = -1
        self._is_frozen = False
        self._is_recognizing = False
        self._status_message = "请选择相机或导入图片"

    @property
    def visual_config(self) -> VisualConfig:
        return self._visual_config

    @property
    def original_frame(self) -> ImageFrame | None:
        return self._original_frame

    @property
    def blocks(self) -> tuple[OcrBlock, ...]:
        return self._blocks

    @property
    def current_block_index(self) -> int:
        return self._current_block_index

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    @property
    def is_recognizing(self) -> bool:
        return self._is_recognizing

    @property
    def state(self) -> SessionState:
        return self._session.state

    def set_original_frame(self, frame: ImageFrame) -> None:
        self._original_frame = frame
        self.original_frame_changed.emit(frame)

    def set_visual_config(self, config: VisualConfig) -> None:
        self._visual_config = config
        self.visual_config_changed.emit(config)

    def set_status(self, message: str) -> None:
        self._status_message = message
        self.status_message_changed.emit(message)

    def on_frame_captured(self, frame: ImageFrame) -> None:
        """相机帧回调（由相机线程调用）。"""
        if not self._is_frozen and not self._is_recognizing:
            self.set_original_frame(frame)

    def freeze(self) -> None:
        """冻结当前帧。"""
        if self._original_frame is None:
            self.error_occurred.emit("没有可冻结的帧")
            return
        try:
            self._session.freeze(self._original_frame.frame_id)
            self._is_frozen = True
            self.is_frozen_changed.emit(True)
            self.set_status("已冻结 - 请选择要识别的段落")
            self.state_changed.emit(self._session.state.value)
        except Exception as e:
            self.error_occurred.emit(f"冻结失败: {e}")

    def unfreeze(self) -> None:
        """解冻。"""
        try:
            self._session.unfreeze()
            self._is_frozen = False
            self._blocks = ()
            self.is_frozen_changed.emit(False)
            self.set_status("实时预览中")
            self.state_changed.emit(self._session.state.value)
        except Exception as e:
            self.error_occurred.emit(f"解冻失败: {e}")

    def start_recognizing(self) -> str:
        """开始识别，返回 request_id。"""
        self._is_recognizing = True
        self.is_recognizing_changed.emit(True)
        self.set_status("正在识别...")
        return self._session.start_recognizing()

    def on_recognition_complete(self, result: OcrResult) -> None:
        """识别完成回调。"""
        self._is_recognizing = False
        self.is_recognizing_changed.emit(False)
        self._blocks = result.blocks
        self._current_block_index = 0 if result.blocks else -1
        self.blocks_changed.emit(list(result.blocks))
        self.current_block_changed.emit(self._current_block_index)

        if result.blocks:
            self._session.finish_recognizing()
            self.set_status(f"识别完成 - {result.block_count} 个文字块（未核对）")
        else:
            self.set_status("未检测到文字，请调整选区或使用原图阅读")
        self.state_changed.emit(self._session.state.value)

    def on_recognition_error(self, error: str) -> None:
        """识别错误回调。"""
        self._is_recognizing = False
        self.is_recognizing_changed.emit(False)
        self.error_occurred.emit(f"识别失败: {error}")
        self.set_status("识别失败 - 原图仍可使用")

    def cancel_recognizing(self) -> None:
        """取消识别。"""
        self._is_recognizing = False
        self.is_recognizing_changed.emit(False)
        try:
            self._session.cancel_recognizing()
        except Exception:
            pass
        self.set_status("已取消识别")
        self.state_changed.emit(self._session.state.value)

    def navigate_next_block(self) -> None:
        """下一段。"""
        if self._current_block_index < len(self._blocks) - 1:
            self._current_block_index += 1
            self.current_block_changed.emit(self._current_block_index)

    def navigate_prev_block(self) -> None:
        """上一段。"""
        if self._current_block_index > 0:
            self._current_block_index -= 1
            self.current_block_changed.emit(self._current_block_index)

    def set_zoom(self, zoom: float) -> None:
        try:
            config = self._visual_config.with_zoom(zoom)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"缩放设置失败: {e}")

    def set_visual_mode(self, mode: VisualMode) -> None:
        try:
            config = self._visual_config.with_mode(mode)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"模式切换失败: {e}")

    def set_contrast(self, contrast: float) -> None:
        try:
            config = self._visual_config.with_contrast(contrast)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"对比度设置失败: {e}")

    def set_eye_care(self, enabled: bool) -> None:
        try:
            config = self._visual_config.with_eye_care(enabled)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"护眼模式设置失败: {e}")

    def set_font_size(self, size: int) -> None:
        try:
            config = self._visual_config.with_font_size(size)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"字号设置失败: {e}")

    def set_line_spacing(self, spacing: float) -> None:
        try:
            config = self._visual_config.with_line_spacing(spacing)
            self.set_visual_config(config)
        except Exception as e:
            self.error_occurred.emit(f"行距设置失败: {e}")

    def new_session(self) -> None:
        """重新输入。"""
        self._session.new_session()
        self._original_frame = None
        self._reading_document = None
        self._blocks = ()
        self._current_block_index = -1
        self._is_frozen = False
        self._is_recognizing = False
        self.is_frozen_changed.emit(False)
        self.is_recognizing_changed.emit(False)
        self.blocks_changed.emit([])
        self.set_status("请选择相机或导入图片")
        self.state_changed.emit(self._session.state.value)