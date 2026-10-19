"""领域异常体系。

所有异常不含任何外部 SDK 类型，可被应用层与适配器层捕获区分。
"""

from __future__ import annotations


class DomainError(Exception):
    """领域异常基类。"""


class ImageFrameValidationError(DomainError):
    """ImageFrame 校验失败。"""


class OcrBlockValidationError(DomainError):
    """OcrBlock 校验失败。"""


class VisualConfigValidationError(DomainError):
    """VisualConfig 超范围或非法。"""


class ImageDecodeError(DomainError):
    """图片解码失败。"""


class UnsupportedImageFormatError(DomainError):
    """不支持的图片格式。"""


class CameraError(DomainError):
    """相机错误。"""


class CameraPermissionDeniedError(CameraError):
    """相机权限被拒绝。"""


class CameraDisconnectedError(CameraError):
    """相机断开。"""


class OcrEngineError(DomainError):
    """OCR 引擎错误。"""


class OcrEngineNotReadyError(OcrEngineError):
    """OCR 引擎未就绪。"""


class ModelLoadError(OcrEngineError):
    """模型加载失败。"""


class PreferenceStoreError(DomainError):
    """偏好存储错误。"""


class SessionStateError(DomainError):
    """会话状态机非法迁移。"""