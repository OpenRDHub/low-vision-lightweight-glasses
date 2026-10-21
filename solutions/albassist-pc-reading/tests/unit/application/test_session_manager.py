"""SessionManager 测试。"""

from __future__ import annotations

import pytest

from albassist.application.session_manager import SessionManager, SessionState
from albassist.domain.exceptions import SessionStateError


class TestSessionManager:
    def test_initial_state(self) -> None:
        sm = SessionManager()
        assert sm.state == SessionState.IDLE

    def test_start_preview(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        assert sm.state == SessionState.PREVIEWING

    def test_freeze(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        assert sm.state == SessionState.FROZEN
        assert sm.frame_id == "frame-1"
        assert sm.frame_revision == 1

    def test_freeze_increments_revision(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.unfreeze()
        sm.freeze("frame-2")
        assert sm.frame_revision == 2

    def test_unfreeze_clears_frame(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.unfreeze()
        assert sm.state == SessionState.PREVIEWING
        assert sm.frame_id == ""

    def test_start_recognizing_returns_request_id(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.start_selecting()
        request_id = sm.start_recognizing()
        assert request_id != ""
        assert sm.state == SessionState.RECOGNIZING

    def test_finish_recognizing(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.start_selecting()
        sm.start_recognizing()
        sm.finish_recognizing()
        assert sm.state == SessionState.READING

    def test_cancel_recognizing(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.start_selecting()
        sm.start_recognizing()
        sm.cancel_recognizing()
        assert sm.state == SessionState.FROZEN

    def test_new_session(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        old_session = sm.session_id
        sm.new_session()
        assert sm.session_id != old_session
        assert sm.state == SessionState.IDLE

    def test_invalid_transition(self) -> None:
        sm = SessionManager()
        with pytest.raises(SessionStateError):
            sm.freeze("frame-1")

    def test_get_current_identity(self) -> None:
        sm = SessionManager()
        sm.start_preview()
        sm.freeze("frame-1")
        sm.start_selecting()
        request_id = sm.start_recognizing()
        identity = sm.get_current_identity()
        assert identity.session_id == sm.session_id
        assert identity.request_id == request_id
        assert identity.frame_id == "frame-1"