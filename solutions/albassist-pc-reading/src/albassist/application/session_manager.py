"""会话管理与状态机。

管理 SessionId/FrameId/RequestId/FrameRevision 四元标识，
状态机流转 Idle→Previewing→Frozen→Selecting→Recognizing→Reading。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum

from albassist.domain.exceptions import SessionStateError
from albassist.domain.models.ocr_models import SessionIdentity


class SessionState(Enum):
    """会话状态枚举。"""

    IDLE = "idle"
    PREVIEWING = "previewing"
    FROZEN = "frozen"
    SELECTING = "selecting"
    RECOGNIZING = "recognizing"
    READING = "reading"


_VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {SessionState.PREVIEWING},
    SessionState.PREVIEWING: {SessionState.FROZEN, SessionState.IDLE},
    SessionState.FROZEN: {SessionState.SELECTING, SessionState.PREVIEWING, SessionState.RECOGNIZING},
    SessionState.SELECTING: {SessionState.RECOGNIZING, SessionState.FROZEN},
    SessionState.RECOGNIZING: {SessionState.READING, SessionState.FROZEN, SessionState.SELECTING},
    SessionState.READING: {
        SessionState.FROZEN,
        SessionState.PREVIEWING,
        SessionState.IDLE,
        SessionState.SELECTING,
    },
}


@dataclass
class SessionManager:
    """会话管理器 - 单写入者聚合根。

    状态由单一 SessionManager 串行更新，不用全局 lock 掩盖状态竞态。
    """

    _session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    _frame_id: str = ""
    _request_id: str = ""
    _frame_revision: int = 0
    _state: SessionState = SessionState.IDLE

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def frame_id(self) -> str:
        return self._frame_id

    @property
    def frame_revision(self) -> int:
        return self._frame_revision

    @property
    def state(self) -> SessionState:
        return self._state

    def new_session(self) -> None:
        """重新输入时递增 SessionId 并释放旧文档引用。"""
        self._session_id = str(uuid.uuid4())
        self._frame_id = ""
        self._request_id = ""
        self._frame_revision = 0
        self._state = SessionState.IDLE

    def start_preview(self) -> None:
        self._transition(SessionState.PREVIEWING)

    def freeze(self, frame_id: str) -> None:
        """冻结当前帧，递增 FrameRevision。"""
        if self._state not in (SessionState.PREVIEWING, SessionState.READING):
            raise SessionStateError(f"不能从 {self._state} 冻结")
        self._frame_id = frame_id
        self._frame_revision += 1
        self._state = SessionState.FROZEN

    def unfreeze(self) -> None:
        """解冻 - 清除旧选区，回到预览。"""
        self._frame_id = ""
        self._transition(SessionState.PREVIEWING)

    def start_selecting(self) -> None:
        self._transition(SessionState.SELECTING)

    def start_recognizing(self) -> str:
        """开始识别，返回新的 request_id。"""
        self._transition(SessionState.RECOGNIZING)
        self._request_id = str(uuid.uuid4())
        return self._request_id

    def finish_recognizing(self) -> None:
        """识别完成，进入阅读状态。"""
        self._transition(SessionState.READING)

    def cancel_recognizing(self) -> None:
        """取消识别，回到冻结状态。"""
        if self._state != SessionState.RECOGNIZING:
            raise SessionStateError(f"不能从 {self._state} 取消识别")
        self._state = SessionState.FROZEN

    def get_current_identity(self) -> SessionIdentity:
        """获取当前瞬间的不可变快照。

        不缓存，并发下返回当前瞬间值。
        """
        return SessionIdentity(
            self._session_id, self._request_id, self._frame_id, self._frame_revision
        )

    def _transition(self, target: SessionState) -> None:
        if target not in _VALID_TRANSITIONS.get(self._state, set()):
            raise SessionStateError(f"非法状态迁移: {self._state} → {target}")
        self._state = target