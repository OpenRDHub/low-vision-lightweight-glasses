"""Qt 输出适配器 - 将 RenderModel 渲染到 Qt 视图。"""

from __future__ import annotations

from albassist.application.ports.output_adapter import IOutputAdapter, RenderModel


class QtOutputAdapter:
    """Qt 输出适配器 - 实现 IOutputAdapter 语义。

    将视图无关的 RenderModel 渲染到 Qt 视图。
    应用层只产生 RenderModel 不接触 QImage/QPixmap。
    """

    def __init__(self, main_window: object) -> None:
        self._window = main_window

    async def render_async(
        self,
        model: RenderModel,
        cancel_token: object | None = None,
    ) -> None:
        """渲染 RenderModel 到 Qt 视图。

        调用应在 UI 线程执行；后台线程请先通过 Qt signal/slot 投递。
        """
        if cancel_token is not None and getattr(cancel_token, "is_cancelled", False):
            return

        original_view = getattr(self._window, "_original_view", None)
        reading_view = getattr(self._window, "_reading_view", None)
        if original_view is None or reading_view is None:
            raise TypeError("main_window 必须提供 _original_view 和 _reading_view 视图")

        # None 表示当前会话没有图像，清空视图避免显示上一会话的残影。
        if model.original_frame is None:
            original_view.set_frame(None)
        else:
            original_view.set_frame(model.original_frame)

        original_view.set_config(model.visual_config)
        original_view.set_frozen(model.is_frozen)
        reading_view.set_config(model.visual_config)
        reading_view.set_blocks(list(model.blocks))
        reading_view.set_current_block(model.current_block_index)

        switch_view = getattr(self._window, "_switch_view", None)
        if callable(switch_view):
            switch_view(2 if model.view_mode == "reading" else 1)

        status_label = getattr(self._window, "_status_label", None)
        if status_label is not None:
            status_label.setText(model.status_message or "")