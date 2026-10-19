"""远近场景双档模型。

对应社群痛点：单筒望远镜看黑板需「不停翻转/手动对焦/一直举手」。
黑板模式与读写模式各自独立记忆显示参数，单键切换、零对焦操作。

Domain 纯净：不依赖 cv2/numpy/Qt。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from albassist.domain.models.visual_config import VisualConfig


class SceneProfileKind(Enum):
    """场景档位。

    READING: 近距读写（课本/作业，近距离对焦，默认档）。
    BLACKBOARD: 远距看板（黑板/投影，远距离、高缩放起点）。
    """

    READING = "reading"
    BLACKBOARD = "blackboard"


_BLACKBOARD_DEFAULT_ZOOM = 4.0


@dataclass
class SceneProfileManager:
    """管理两档场景各自的 VisualConfig。

    切换档位时保存当前配置到旧档、装载新档配置。
    每档独立，改黑板档缩放不影响读写档。
    """

    _current: SceneProfileKind = SceneProfileKind.READING
    _configs: dict[SceneProfileKind, VisualConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._configs:
            self._configs = {
                SceneProfileKind.READING: VisualConfig(),
                SceneProfileKind.BLACKBOARD: VisualConfig().with_zoom(
                    _BLACKBOARD_DEFAULT_ZOOM
                ),
            }

    @property
    def current(self) -> SceneProfileKind:
        return self._current

    @property
    def config(self) -> VisualConfig:
        """当前档位配置。"""
        return self._configs[self._current]

    def switch_to(self, kind: SceneProfileKind) -> VisualConfig:
        """切换档位，返回新档位配置。

        当前配置已在 set_config 时保存，这里直接装载目标档。
        """
        self._current = kind
        return self._configs[kind]

    def toggle(self) -> VisualConfig:
        """在读写档与黑板档之间切换。"""
        target = (
            SceneProfileKind.BLACKBOARD
            if self._current is SceneProfileKind.READING
            else SceneProfileKind.READING
        )
        return self.switch_to(target)

    def set_config(self, config: VisualConfig) -> None:
        """更新当前档位配置（另一档不受影响）。"""
        self._configs[self._current] = config
