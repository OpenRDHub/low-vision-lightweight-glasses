"""主窗口 - 承载原图视图与大字阅读版，工具栏与状态栏。"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Protocol, runtime_checkable

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from albassist.application.ports.camera_source import CameraDevice, ICameraSource
from albassist.domain.models.ocr_models import OcrBlock
from albassist.domain.models.visual_config import VisualMode
from albassist.presentation.services.keyboard_router import KeyboardRouter
from albassist.presentation.views.original_view import OriginalView
from albassist.presentation.views.reading_view import ReadingView
from albassist.presentation.view_models.main_view_model import MainViewModel


_STYLE_PATH = Path(__file__).parent / "resources" / "styles" / "style.qss"


@runtime_checkable
class _FaceAlertController(Protocol):
    """人脸提醒控制器端口 - 表示层仅需 set_enabled 能力。"""

    def set_enabled(self, enabled: bool) -> None: ...


class MainWindow(QMainWindow):
    """主窗口。"""

    _devices_found = Signal(object)
    _camera_error = Signal(str)

    def __init__(self, view_model: MainViewModel, camera_source: ICameraSource | None = None, face_alert: _FaceAlertController | None = None) -> None:
        super().__init__()
        self._vm = view_model
        self._camera_source = camera_source
        self._face_alert = face_alert
        self.setWindowTitle("Albassist - AI 助视学习软件")
        self.setMinimumSize(1024, 768)

        self._load_style()

        self._stack = QStackedWidget()
        self._original_view = OriginalView()
        self._reading_view = ReadingView()
        self._input_widget = self._build_input_widget()

        self._stack.addWidget(self._input_widget)
        self._stack.addWidget(self._original_view)
        self._stack.addWidget(self._reading_view)
        self.setCentralWidget(self._stack)

        self._build_menubar()
        self._build_toolbar()
        self._build_statusbar()

        self._keyboard = KeyboardRouter()
        self._setup_keyboard()
        self._keyboard.install(self)

        self._connect_signals()
        if self._face_alert is not None:
            self._act_face_alert.toggled.connect(self._face_alert.set_enabled)
        self._setup_rest_reminder()

    def _setup_rest_reminder(self) -> None:
        """20-20-20 护眼法则：每 20 分钟提醒看 6 米外 20 秒。"""
        self._rest_timer = QTimer(self)
        self._rest_timer.setInterval(20 * 60 * 1000)
        self._rest_timer.timeout.connect(
            lambda: self._vm.info_message.emit(
                "护眼提醒：已连续使用 20 分钟，请远眺 6 米外 20 秒"
            )
        )
        self._rest_timer.start()

    def _load_style(self) -> None:
        if _STYLE_PATH.exists():
            with open(_STYLE_PATH, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _build_input_widget(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("input_selection")
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        title = QLabel("Albassist - AI 助视学习软件")
        title.setProperty("role", "heading")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("面向白化病低视力学生的室内学习阅读工具")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 18px; color: #666;")
        layout.addWidget(subtitle)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        btn_row.setSpacing(20)

        self._btn_camera = QPushButton("📷  选择相机")
        self._btn_camera.setMinimumSize(220, 64)
        self._btn_import = QPushButton("📁  导入图片 (Ctrl+O)")
        self._btn_import.setMinimumSize(220, 64)

        btn_row.addWidget(self._btn_camera)
        btn_row.addWidget(self._btn_import)
        layout.addLayout(btn_row)

        steps = QLabel(
            "操作流程: 选择输入 → 实时预览 → 按 F 冻结 → 鼠标框选文字 → 按 R 识别 → 看大字阅读版\n"
            "快捷键: F=冻结  R=识别  O=看原图  L=看大字  G=灰度  I=反色  C=对比度  +=放大  -=缩小"
        )
        steps.setAlignment(Qt.AlignCenter)
        steps.setStyleSheet("font-size: 16px; color: #888; padding: 12px;")
        layout.addWidget(steps)

        return widget

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self._act_freeze = QAction("冻结 (F)", self)
        self._act_recognize = QAction("识别 (R)", self)
        self._act_cancel = QAction("取消 (Esc)", self)
        self._act_view_original = QAction("看原图 (O)", self)
        self._act_view_reading = QAction("看大字 (L)", self)

        toolbar.addAction(self._act_freeze)
        toolbar.addAction(self._act_recognize)
        toolbar.addAction(self._act_cancel)
        toolbar.addSeparator()
        toolbar.addAction(self._act_view_original)
        toolbar.addAction(self._act_view_reading)
        toolbar.addSeparator()

        toolbar.addWidget(QLabel("缩放:"))
        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(10, 160)
        self._zoom_slider.setValue(10)
        self._zoom_slider.setFixedWidth(180)
        toolbar.addWidget(self._zoom_slider)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("对比度:"))
        self._contrast_slider = QSlider(Qt.Horizontal)
        self._contrast_slider.setRange(0, 200)
        self._contrast_slider.setValue(100)
        self._contrast_slider.setFixedWidth(150)
        toolbar.addWidget(self._contrast_slider)

    def _build_menubar(self) -> None:
        """菜单栏 - 视觉模式与工具功能，避免工具栏溢出。"""
        menubar = self.menuBar()

        mode_menu = menubar.addMenu("视觉模式")
        self._act_mode_original = QAction("原色 (N)", self)
        self._act_mode_gray = QAction("灰度 (G)", self)
        self._act_mode_invert = QAction("反色 (I)", self)
        self._act_mode_contrast = QAction("对比度 (C)", self)
        self._act_mode_binarize = QAction("二值化 (B)", self)
        self._act_mode_local_contrast = QAction("局部增强 (E)", self)
        self._act_eye_care = QAction("护眼 (W)", self)
        self._act_eye_care.setCheckable(True)
        mode_menu.addAction(self._act_mode_original)
        mode_menu.addAction(self._act_mode_gray)
        mode_menu.addAction(self._act_mode_invert)
        mode_menu.addAction(self._act_mode_contrast)
        mode_menu.addAction(self._act_mode_binarize)
        mode_menu.addAction(self._act_mode_local_contrast)
        mode_menu.addSeparator()
        mode_menu.addAction(self._act_eye_care)

        tool_menu = menubar.addMenu("工具")
        self._act_face_alert = QAction("人脸提醒", self)
        self._act_face_alert.setCheckable(True)
        self._act_face_alert.setToolTip("开启后检测到人脸时语音播报（离线）")
        tool_menu.addAction(self._act_face_alert)

    def _build_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("请选择相机或导入图片")
        self._statusbar.addWidget(self._status_label, 1)

        self._freeze_indicator = QLabel()
        self._freeze_indicator.setObjectName("freeze_indicator")
        self._freeze_indicator.hide()
        self._statusbar.addPermanentWidget(self._freeze_indicator)

    def _setup_keyboard(self) -> None:
        self._keyboard.register_action("toggle_freeze", self._on_toggle_freeze)
        self._keyboard.register_action("recognize", self._on_recognize)
        self._keyboard.register_action("cancel_or_back", self._on_cancel)
        self._keyboard.register_action("toggle_view", self._on_toggle_view)
        self._keyboard.register_action("next_block", self._vm.navigate_next_block)
        self._keyboard.register_action("prev_block", self._vm.navigate_prev_block)
        self._keyboard.register_action("view_original", lambda: self._switch_view(1))
        self._keyboard.register_action("view_reading", lambda: self._switch_view(2))
        self._keyboard.register_action("zoom_in", lambda: self._vm.set_zoom(min(8.0, self._vm.visual_config.zoom_factor + 0.5)))
        self._keyboard.register_action("zoom_out", lambda: self._vm.set_zoom(max(1.0, self._vm.visual_config.zoom_factor - 0.5)))
        self._keyboard.register_action("zoom_reset", lambda: self._vm.set_zoom(1.0))
        self._keyboard.register_action("mode_grayscale", lambda: self._vm.set_visual_mode(VisualMode.GRAYSCALE))
        self._keyboard.register_action("mode_invert", lambda: self._vm.set_visual_mode(VisualMode.INVERT))
        self._keyboard.register_action("mode_original", lambda: self._vm.set_visual_mode(VisualMode.ORIGINAL))
        self._keyboard.register_action("mode_contrast", lambda: self._vm.set_visual_mode(VisualMode.CONTRAST))
        self._keyboard.register_action("mode_binarize", lambda: self._vm.set_visual_mode(VisualMode.BINARIZE))
        self._keyboard.register_action("mode_local_contrast", lambda: self._vm.set_visual_mode(VisualMode.LOCAL_CONTRAST))
        self._keyboard.register_action("toggle_eye_care", self._on_toggle_eye_care)
        self._keyboard.register_action("font_inc", lambda: self._vm.set_font_size(min(96, self._vm.visual_config.font_size + 4)))
        self._keyboard.register_action("font_dec", lambda: self._vm.set_font_size(max(24, self._vm.visual_config.font_size - 4)))
        self._keyboard.register_action("import_image", self._on_import_image)
        # 这两项属于尚未接入 UI 的 P1 能力，不再绑定空回调，明确反馈当前状态。
        self._keyboard.register_action("toggle_tts", self._on_tts_unavailable)
        self._keyboard.register_action("save_preset", self._on_preset_unavailable)

    def _connect_signals(self) -> None:
        self._devices_found.connect(self._show_camera_choice)
        self._camera_error.connect(self._vm.error_occurred.emit)

        self._btn_camera.clicked.connect(self._on_select_camera)

        self._btn_import.clicked.connect(self._on_import_image)

        self._act_freeze.triggered.connect(self._on_toggle_freeze)
        self._act_recognize.triggered.connect(self._on_recognize)
        self._act_cancel.triggered.connect(self._on_cancel)
        self._act_view_original.triggered.connect(lambda: self._switch_view(1))
        self._act_view_reading.triggered.connect(lambda: self._switch_view(2))

        self._zoom_slider.valueChanged.connect(lambda v: self._vm.set_zoom(v / 10.0))
        self._contrast_slider.valueChanged.connect(lambda v: self._vm.set_contrast(v / 100.0))

        self._act_mode_original.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.ORIGINAL))
        self._act_mode_gray.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.GRAYSCALE))
        self._act_mode_invert.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.INVERT))
        self._act_mode_contrast.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.CONTRAST))
        self._act_mode_binarize.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.BINARIZE))
        self._act_mode_local_contrast.triggered.connect(lambda: self._vm.set_visual_mode(VisualMode.LOCAL_CONTRAST))
        self._act_eye_care.toggled.connect(self._on_eye_care_action_toggled)

        self._vm.status_message_changed.connect(self._status_label.setText)
        self._vm.info_message.connect(self._status_label.setText)
        self._vm.info_message.connect(lambda msg: self.show_temporary_message(msg))
        self._vm.original_frame_changed.connect(self._on_frame_changed)
        self._vm.visual_config_changed.connect(self._on_config_changed)
        self._vm.is_frozen_changed.connect(self._on_frozen_changed)
        self._vm.is_recognizing_changed.connect(self._on_recognizing_changed)
        self._vm.blocks_changed.connect(self._on_blocks_changed)
        self._vm.current_block_changed.connect(self._reading_view.set_current_block)
        self._vm.current_block_changed.connect(self._on_current_block_changed)
        self._vm.error_occurred.connect(self._on_error)

        self._original_view.selection_changed.connect(self._on_selection_changed)
        self._reading_view.view_original_requested.connect(lambda: self._switch_view(1))
        self._reading_view.next_block_requested.connect(self._vm.navigate_next_block)
        self._reading_view.prev_block_requested.connect(self._vm.navigate_prev_block)
        self._reading_view.font_size_changed.connect(self._vm.set_font_size)
        self._reading_view.line_spacing_changed.connect(self._vm.set_line_spacing)

    def _on_select_camera(self) -> None:
        self._switch_view(1)
        self._status_label.setText("正在搜索摄像头...")

        if self._camera_source is None:
            self._vm.error_occurred.emit("相机模块未初始化")
            return

        def _scan() -> None:
            import asyncio

            async def _run() -> None:
                camera = self._camera_source
                if camera is None:
                    return
                devices = await camera.list_async()
                if not devices:
                    self._camera_error.emit("未找到摄像头设备，请检查连接")
                    return
                self._devices_found.emit(devices)

            try:
                asyncio.run(_run())
            except Exception as e:
                self._camera_error.emit(f"相机搜索失败: {e}")

        threading.Thread(target=_scan, daemon=True, name="camera-scan").start()

    def _show_camera_choice(self, devices: list[CameraDevice]) -> None:
        """显示摄像头选择对话框，单个设备直接启动。"""
        if len(devices) == 1:
            self._start_camera(devices[0])
            return

        items = [d.name for d in devices]
        choice, ok = QInputDialog.getItem(
            self, "选择摄像头", f"检测到 {len(devices)} 个摄像头，请选择：", items, 0, False
        )
        if ok:
            self._start_camera(devices[items.index(choice)])
        else:
            self._vm.set_status("已取消摄像头选择")

    def _start_camera(self, device: CameraDevice) -> None:
        """启动选定的摄像头。"""
        self._status_label.setText(f"正在启动 {device.name}...")

        def _start() -> None:
            import asyncio

            async def _run() -> None:
                camera = self._camera_source
                if camera is None:
                    return
                camera.set_error_callback(
                    lambda msg: self._vm.error_occurred.emit(msg)
                )
                await camera.start_async(
                    device.device_id,
                    self._vm.on_frame_captured,
                )
                self._vm.set_status(f"相机已连接 - {device.name}（按 F 冻结）")

            try:
                asyncio.run(_run())
            except Exception as e:
                self._vm.error_occurred.emit(f"相机启动失败: {e}")

        threading.Thread(target=_start, daemon=True, name="camera-start").start()

    def _on_select_network_camera(self) -> None:
        """连接显式配置的局域网 MJPEG 摄像头。"""
        if self._camera_source is None:
            self._vm.error_occurred.emit("相机模块未初始化")
            return

        device_id = "mjpeg|http://192.168.84.243:8080/stream.mjpg"
        self._switch_view(1)
        self._status_label.setText("正在连接局域网摄像头...")

        def _start() -> None:
            import asyncio

            async def _run() -> None:
                camera = self._camera_source
                if camera is None:
                    return
                camera.set_error_callback(
                    lambda msg: self._vm.error_occurred.emit(msg)
                )
                await camera.start_async(
                    device_id,
                    self._vm.on_frame_captured,
                )
                self._vm.set_status("局域网摄像头已连接 - MJPEG（按 F 冻结）")

            try:
                asyncio.run(_run())
            except Exception as exc:
                self._vm.error_occurred.emit(f"局域网摄像头启动失败: {exc}")

        threading.Thread(target=_start, daemon=True, name="network-camera-start").start()

    def _on_import_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "导入图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._vm.import_image_requested.emit(path)

    def _on_toggle_freeze(self) -> None:
        if self._vm.is_frozen:
            self._vm.unfreeze()
        else:
            self._vm.freeze()

    def _on_toggle_eye_care(self) -> None:
        self._act_eye_care.setChecked(not self._vm.visual_config.eye_care)

    def _on_eye_care_action_toggled(self, enabled: bool) -> None:
        if enabled == self._vm.visual_config.eye_care:
            return
        self._vm.set_eye_care(enabled)
        self._vm.set_status(
            "数字护眼模式已开启 - 仅调整显示配色，不改变原图或硬件亮度"
            if enabled
            else "数字护眼模式已关闭"
        )

    def _on_recognize(self) -> None:
        if self._vm.is_frozen and not self._vm.is_recognizing:
            selection = self._original_view.get_selection()
            if not selection.is_empty:
                self._vm.recognize_requested.emit(selection)
            else:
                self._vm.error_occurred.emit("请先用鼠标在画面上框选要识别的文字区域")

    def _on_cancel(self) -> None:
        if self._vm.is_recognizing:
            self._vm.cancel_requested.emit()

    def _on_toggle_view(self) -> None:
        if self._stack.currentIndex() == 1:
            self._switch_view(2)
        else:
            self._switch_view(1)

    def _switch_view(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    def _on_frame_changed(self, frame: object) -> None:
        self._original_view.set_frame(frame)  # type: ignore[arg-type]

    def _on_config_changed(self, config: object) -> None:
        self._original_view.set_config(config)  # type: ignore[arg-type]
        self._reading_view.set_config(config)  # type: ignore[arg-type]
        self._act_eye_care.blockSignals(True)
        self._act_eye_care.setChecked(self._vm.visual_config.eye_care)
        self._act_eye_care.blockSignals(False)
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(int(self._vm.visual_config.zoom_factor * 10))
        self._zoom_slider.blockSignals(False)
        self._contrast_slider.blockSignals(True)
        self._contrast_slider.setValue(int(self._vm.visual_config.contrast_level * 100))
        self._contrast_slider.blockSignals(False)

    def _on_frozen_changed(self, frozen: bool) -> None:
        self._original_view.set_frozen(frozen)
        if frozen:
            self._freeze_indicator.setText(" 已冻结 ")
            self._freeze_indicator.show()
            self._act_freeze.setText("解冻 (F)")
        else:
            self._freeze_indicator.hide()
            self._original_view.clear_selection()
            self._act_freeze.setText("冻结 (F)")

    def _on_recognizing_changed(self, recognizing: bool) -> None:
        self._act_recognize.setEnabled(not recognizing)
        self._act_cancel.setEnabled(recognizing)

    def _on_blocks_changed(self, blocks: list[OcrBlock]) -> None:
        self._reading_view.set_blocks(blocks)
        if blocks:
            self._switch_view(2)

    def _on_selection_changed(self, x: int, y: int, w: int, h: int) -> None:
        """更新状态栏选区信息；OCR 在用户主动按 R 后才提交。"""
        if w <= 0 or h <= 0:
            return
        self._vm.set_status(f"已选择原图区域 {w} × {h} 像素，按 R 识别")

    def _on_tts_unavailable(self) -> None:
        self._vm.info_message.emit("朗读功能尚未接入当前界面；请使用已验证的 Windows 版本。")

    def _on_preset_unavailable(self) -> None:
        self._vm.info_message.emit("个人预设保存尚未接入当前界面。")

    def _on_current_block_changed(self, index: int) -> None:
        blocks = self._vm.blocks
        if 0 <= index < len(blocks):
            self._original_view.set_highlight(blocks[index].source_rect)
        else:
            self._original_view.set_highlight(None)

    def _on_error(self, message: str) -> None:
        self._status_label.setText(f"错误: {message}")
    def show_temporary_message(self, message: str) -> None:
        self._status_label.setText(message)