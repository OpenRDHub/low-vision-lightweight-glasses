"""全键盘路由 - 所有 P0 操作可仅用键盘完成。

焦点清晰可见，快捷键不占用 Windows 系统保留组合。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut


@dataclass(frozen=True)
class KeyBinding:
    """快捷键绑定。"""

    key_sequence: str
    description: str
    action_name: str


_DEFAULT_BINDINGS: list[KeyBinding] = [
    KeyBinding("F", "冻结/解冻", "toggle_freeze"),
    KeyBinding("R", "识别选区", "recognize"),
    KeyBinding("Escape", "取消/返回", "cancel_or_back"),
    KeyBinding("Space", "切换视图", "toggle_view"),
    KeyBinding("Right", "下一段", "next_block"),
    KeyBinding("Left", "上一段", "prev_block"),
    KeyBinding("O", "看原图", "view_original"),
    KeyBinding("L", "看大字", "view_reading"),
    KeyBinding("+", "放大", "zoom_in"),
    KeyBinding("-", "缩小", "zoom_out"),
    KeyBinding("0", "恢复整页", "zoom_reset"),
    KeyBinding("G", "灰度模式", "mode_grayscale"),
    KeyBinding("I", "反色模式", "mode_invert"),
    KeyBinding("N", "原色模式", "mode_original"),
    KeyBinding("C", "对比度模式", "mode_contrast"),
    KeyBinding("B", "二值化(粉笔字)", "mode_binarize"),
    KeyBinding("E", "局部对比度增强", "mode_local_contrast"),
    KeyBinding("W", "护眼模式", "toggle_eye_care"),
    KeyBinding("T", "朗读（P1）", "toggle_tts"),
    KeyBinding("Ctrl+O", "导入图片", "import_image"),
    KeyBinding("Ctrl+S", "保存预设（P1）", "save_preset"),
    KeyBinding("]", "字号增大", "font_inc"),
    KeyBinding("[", "字号减小", "font_dec"),
]


class KeyboardRouter(QObject):
    """键盘路由器 - 管理快捷键绑定与分发。"""

    action_triggered = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._shortcuts: list[QShortcut] = []
        self._bindings: list[KeyBinding] = list(_DEFAULT_BINDINGS)
        self._actions: dict[str, Callable[[], None]] = {}

    def register_action(self, name: str, callback: Callable[[], None]) -> None:
        """注册动作回调。"""
        self._actions[name] = callback

    def install(self, parent: QObject) -> None:
        """在父对象上安装所有快捷键。"""
        for binding in self._bindings:
            shortcut = QShortcut(QKeySequence(binding.key_sequence), parent)
            shortcut.activated.connect(lambda b=binding: self._on_activated(b))
            shortcut.setContext(Qt.ApplicationShortcut)
            self._shortcuts.append(shortcut)

    def _on_activated(self, binding: KeyBinding) -> None:
        action = self._actions.get(binding.action_name)
        if action is not None:
            action()
        self.action_triggered.emit(binding.action_name)

    @property
    def bindings(self) -> list[KeyBinding]:
        """所有快捷键绑定（用于帮助显示）。"""
        return list(self._bindings)

    def get_help_text(self) -> str:
        """获取快捷键帮助文本。"""
        lines = ["快捷键说明:"]
        for b in self._bindings:
            lines.append(f"  {b.key_sequence:<12} - {b.description}")
        return "\n".join(lines)