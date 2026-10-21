"""用户偏好与预设模型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class UserPreference:
    """用户偏好键值对。

    仅持久化用户主动选择的显示偏好；不保存图像/OCR 正文/阅读历史。
    """

    key: str
    value: str
    updated_at: datetime

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UserPreset:
    """用户预设 - 命名阅读方案。

    不依据诊断或摄像头自动生成；用户主动切换。
    """

    id: int | None
    name: str
    config_json: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("预设名称不能为空")
        if not self.config_json:
            raise ValueError("config_json 不能为空")