"""组合根 - 集中装配所有端口实现。

唯一允许 import 具体适配器类的位置。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
import warnings

from albassist.application.ports.camera_source import ICameraSource
from albassist.application.ports.image_importer import IImageImporter
from albassist.application.ports.image_processor import IImageProcessor
from albassist.application.ports.ocr_engine import IOcrEngine
from albassist.application.ports.output_adapter import IOutputAdapter
from albassist.application.ports.preference_store import IUserPreferenceStore
from albassist.application.ports.tts_engine import ITtsEngine
from albassist.application.ports.face_detector import IFaceDetector
from albassist.application.session_manager import SessionManager
from albassist.application.use_cases.recognition_orchestrator import RecognitionOrchestrator
from albassist.app.container import Container
from albassist.domain.models.user_preference import UserPreference
from albassist.domain.models.visual_config import VisualConfig, VisualMode
from albassist.infrastructure.camera_source import CameraSourceAdapter
from albassist.infrastructure.sqlite_preference_store import SqlitePreferenceStore
from albassist.infrastructure.threading.cancel_token import CancellationToken
from albassist.infrastructure.threading.ocr_thread import OcrWorker
from albassist.ocr_runtime.fake_engine import FakeOcrEngine

from albassist.infrastructure.tts_engine import TtsEngineAdapter
from albassist.infrastructure.threading.face_alert_worker import FaceAlertWorker
from albassist.vision.opencv_face_detector import OpenCvFaceDetector
from albassist.vision.opencv_image_importer import OpenCvImageImporter
from albassist.vision.opencv_image_processor import OpenCvImageProcessor


def _make_tts() -> TtsEngineAdapter:
    tts = TtsEngineAdapter()
    tts.initialize()
    return tts


def create_container(
    use_fake_ocr: bool = False,
    db_path: str = "albassist_preferences.db",
    network_camera_urls: tuple[str, ...] = (),
) -> Container:
    """创建并装配 DI 容器。

    Args:
        use_fake_ocr: True 使用 FakeOcrEngine（测试/未通过 M0），
                      False 使用 RapidOcrEngine（不可用时回退 Fake）。
        db_path: SQLite 数据库路径。
    """
    container = Container()

    container.register_factory(
        ICameraSource,
        lambda: CameraSourceAdapter(network_camera_urls),
    )  # type: ignore[type-abstract]
    container.register_factory(IImageImporter, OpenCvImageImporter)  # type: ignore[type-abstract]
    container.register_factory(IImageProcessor, OpenCvImageProcessor)  # type: ignore[type-abstract]

    if use_fake_ocr:
        container.register_factory(IOcrEngine, FakeOcrEngine)  # type: ignore[type-abstract]
    else:
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
            from albassist.ocr_runtime.rapid_engine import RapidOcrEngine
            container.register_factory(IOcrEngine, lambda: RapidOcrEngine())  # type: ignore[type-abstract]
        except Exception:
            import warnings
            warnings.warn(
                "RapidOCR 不可用，回退到 FakeOcrEngine。"
                "请安装 rapidocr-onnxruntime 以启用真实 AI 识别。",
                stacklevel=2,
            )
            container.register_factory(IOcrEngine, FakeOcrEngine)  # type: ignore[type-abstract]

    container.register_factory(  # type: ignore[type-abstract]
        IUserPreferenceStore,
        lambda: SqlitePreferenceStore.load_with_fallback(db_path),
    )

    container.register_factory(SessionManager, SessionManager)

    container.register_factory(ITtsEngine, _make_tts)  # type: ignore[type-abstract]
    # 人脸检测模型缺失时保持未就绪，由 FaceAlertWorker 安全停用；不伪造空结果。
    container.register_factory(IFaceDetector, OpenCvFaceDetector)  # type: ignore[type-abstract]
    container.register_factory(
        FaceAlertWorker,
        lambda: FaceAlertWorker(container.resolve(IFaceDetector), container.resolve(ITtsEngine)),
    )

    return container


async def load_visual_config(store: IUserPreferenceStore) -> VisualConfig:
    """从偏好存储加载 VisualConfig，失败回退默认。"""
    import json

    try:
        pref = await store.load_async("visual_config")
        if pref is not None:
            data = json.loads(pref.value)
            return VisualConfig(
                zoom_factor=data.get("zoom_factor", 1.0),
                visual_mode=VisualMode(data.get("visual_mode", "original")),
                contrast_level=data.get("contrast_level", 1.0),
                font_size=data.get("font_size", 48),
                line_spacing=data.get("line_spacing", 1.5),
                text_color=data.get("text_color", "#000000"),
                background_color=data.get("background_color", "#FFFFFF"),
                binarize_threshold=data.get("binarize_threshold", 127.5),
                eye_care=bool(data.get("eye_care", False)),
            )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        warnings.warn(f"视觉配置加载失败，已回退默认值: {exc}", RuntimeWarning, stacklevel=2)
    return VisualConfig.reset()


def load_visual_config_sync(store: SqlitePreferenceStore) -> VisualConfig:
    """同步从偏好存储加载 VisualConfig，失败回退默认。"""
    import json

    try:
        pref = store.load_sync("visual_config")
        if pref is not None:
            data = json.loads(pref.value)
            return VisualConfig(
                zoom_factor=data.get("zoom_factor", 1.0),
                visual_mode=VisualMode(data.get("visual_mode", "original")),
                contrast_level=data.get("contrast_level", 1.0),
                font_size=data.get("font_size", 48),
                line_spacing=data.get("line_spacing", 1.5),
                text_color=data.get("text_color", "#000000"),
                background_color=data.get("background_color", "#FFFFFF"),
                binarize_threshold=data.get("binarize_threshold", 127.5),
                eye_care=bool(data.get("eye_care", False)),
            )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        warnings.warn(f"视觉配置加载失败，已回退默认值: {exc}", RuntimeWarning, stacklevel=2)
    return VisualConfig.reset()


async def save_visual_config(store: IUserPreferenceStore, config: VisualConfig) -> None:
    """保存 VisualConfig 到偏好存储。"""
    import json

    data = {
        "zoom_factor": config.zoom_factor,
        "visual_mode": config.visual_mode.value,
        "contrast_level": config.contrast_level,
        "font_size": config.font_size,
        "line_spacing": config.line_spacing,
        "text_color": config.text_color,
        "background_color": config.background_color,
        "binarize_threshold": config.binarize_threshold,
        "eye_care": config.eye_care,
    }
    pref = UserPreference(
        key="visual_config",
        value=json.dumps(data),
        updated_at=datetime.now(timezone.utc),
    )
    await store.save_async(pref)


def save_visual_config_sync(store: SqlitePreferenceStore, config: VisualConfig) -> None:
    """同步保存 VisualConfig 到偏好存储。"""
    import json

    data = {
        "zoom_factor": config.zoom_factor,
        "visual_mode": config.visual_mode.value,
        "contrast_level": config.contrast_level,
        "font_size": config.font_size,
        "line_spacing": config.line_spacing,
        "text_color": config.text_color,
        "background_color": config.background_color,
        "binarize_threshold": config.binarize_threshold,
        "eye_care": config.eye_care,
    }
    pref = UserPreference(
        key="visual_config",
        value=json.dumps(data),
        updated_at=datetime.now(timezone.utc),
    )
    store.save_sync(pref)