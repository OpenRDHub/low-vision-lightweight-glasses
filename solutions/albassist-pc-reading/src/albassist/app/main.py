"""应用入口 - QApplication + 装配 + 加载偏好 + exec()。"""

from __future__ import annotations

import sys
import threading

from PySide6.QtWidgets import QApplication

from albassist.app.composition_root import create_container, load_visual_config, save_visual_config
from albassist.application.ports.camera_source import ICameraSource
from albassist.application.ports.image_importer import IImageImporter
from albassist.application.ports.ocr_engine import IOcrEngine
from albassist.application.ports.preference_store import IUserPreferenceStore
from albassist.application.session_manager import SessionManager
from albassist.domain.geometry import ImageRect
from albassist.domain.models.ocr_models import RecognitionRequest
from albassist.domain.models.visual_config import VisualConfig
from albassist.infrastructure.threading.cancel_token import CancellationToken
from albassist.infrastructure.threading.ocr_thread import OcrWorker
from albassist.infrastructure.threading.face_alert_worker import FaceAlertWorker
from albassist.presentation.view_models.main_view_model import MainViewModel
from albassist.presentation.views.main_window import MainWindow


def main() -> int:
    """主入口。"""
    app = QApplication(sys.argv)
    app.setApplicationName("Albassist")
    app.setOrganizationName("Albassist Team")

    container = create_container(
        use_fake_ocr=False,
        network_camera_urls=("http://192.168.84.243:8080/stream.mjpg",),
    )

    session_manager = container.resolve(SessionManager)
    view_model = MainViewModel(session_manager)

    importer = container.resolve(IImageImporter)  # type: ignore[type-abstract]
    ocr_engine = container.resolve(IOcrEngine)  # type: ignore[type-abstract]
    preference_store = container.resolve(IUserPreferenceStore)  # type: ignore[type-abstract]
    camera_source = container.resolve(ICameraSource)  # type: ignore[type-abstract]

    ocr_worker = OcrWorker(
        engine=ocr_engine,
        on_result=view_model.on_recognition_complete,
        on_error=view_model.on_recognition_error,
    )
    ocr_worker.start()

    face_alert = container.resolve(FaceAlertWorker)
    face_alert.start()
    view_model.original_frame_changed.connect(face_alert.on_frame)

    def _warmup() -> None:
        import asyncio
        coro = ocr_engine.warmup_async()
        try:
            asyncio.run(coro)
        except Exception:
            coro.close()

    threading.Thread(target=_warmup, daemon=True, name="ocr-warmup").start()

    window = MainWindow(view_model, camera_source, face_alert)
    window.show()

    def on_import_image(path: str) -> None:
        import asyncio

        async def _load() -> None:
            try:
                frame = await importer.load_async(path)
                view_model.set_original_frame(frame)
                view_model.set_status("图片已导入 - 按 F 冻结")
            except Exception as e:
                view_model.error_occurred.emit(str(e))

        threading.Thread(target=lambda: asyncio.run(_load()), daemon=True, name="image-load").start()

    _active_token: list[CancellationToken | None] = [None]

    def on_recognize(selection: ImageRect) -> None:
        if view_model.original_frame is None:
            return
        if _active_token[0] is not None:
            _active_token[0].cancel()
        request_id = view_model.start_recognizing()
        identity = session_manager.get_current_identity()
        request = RecognitionRequest(
            session_id=identity.session_id,
            request_id=request_id,
            frame_id=identity.frame_id,
            frame_revision=identity.frame_revision,
            region_of_interest=selection,
            image=view_model.original_frame,
        )
        token = CancellationToken()
        _active_token[0] = token
        ocr_worker.submit(request, token)

    def on_cancel_recognize() -> None:
        if _active_token[0] is not None:
            _active_token[0].cancel()
            _active_token[0] = None
        view_model.cancel_recognizing()

    view_model.import_image_requested.connect(on_import_image)
    view_model.recognize_requested.connect(on_recognize)
    view_model.cancel_requested.connect(on_cancel_recognize)

    def _save_config(config: VisualConfig) -> None:
        import asyncio
        try:
            asyncio.run(save_visual_config(preference_store, config))
        except Exception:
            pass

    view_model.visual_config_changed.connect(
        lambda config: threading.Thread(target=_save_config, args=(config,), daemon=True, name="config-save").start()
    )

    def _init_config() -> None:
        import asyncio

        async def _init() -> None:
            config = await load_visual_config(preference_store)
            view_model.set_visual_config(config)

        coro = _init()
        try:
            asyncio.run(coro)
        except Exception:
            coro.close()

    threading.Thread(target=_init_config, daemon=True, name="config-init").start()

    ret = app.exec()

    ocr_worker.stop()
    face_alert.stop()
    if hasattr(preference_store, 'close'):
        preference_store.close()

    return ret


if __name__ == "__main__":
    sys.exit(main())