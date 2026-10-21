"""RecognitionOrchestrator 测试 - 用 Fake 端口测试三态。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from albassist.application.use_cases.recognition_orchestrator import RecognitionOrchestrator
from albassist.application.use_cases.recognition_outcome import RecognitionStatus
from albassist.domain.geometry import ImageRect
from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.ocr_models import (
    OcrBlock,
    OcrResult,
    RecognitionRequest,
    SessionIdentity,
)
from albassist.ocr_runtime.fake_engine import FakeOcrEngine


def _make_frame(frame_id: str = "f1") -> ImageFrame:
    return ImageFrame(
        frame_id=frame_id,
        width=100,
        height=100,
        stride=300,
        pixel_format="RGB24",
        pixels=b"\x00" * (300 * 100),
        captured_at=datetime.now(timezone.utc),
    )


def _make_request(
    session_id: str = "s1",
    request_id: str = "r1",
    frame_id: str = "f1",
    revision: int = 1,
) -> RecognitionRequest:
    return RecognitionRequest(
        session_id=session_id,
        request_id=request_id,
        frame_id=frame_id,
        frame_revision=revision,
        region_of_interest=ImageRect(0, 0, 100, 100),
        image=_make_frame(frame_id),
    )


class TestRecognitionOrchestrator:
    @pytest.mark.asyncio
    async def test_accepted(self) -> None:
        engine = FakeOcrEngine()
        orchestrator = RecognitionOrchestrator(engine)
        request = _make_request()

        def get_current() -> SessionIdentity:
            return SessionIdentity("s1", "r1", "f1", 1)

        outcome = await orchestrator.recognize_async(request, get_current)
        assert outcome.is_accepted
        assert outcome.result is not None

    @pytest.mark.asyncio
    async def test_stale_different_session(self) -> None:
        engine = FakeOcrEngine()
        orchestrator = RecognitionOrchestrator(engine)
        request = _make_request()

        def get_current() -> SessionIdentity:
            return SessionIdentity("s2", "r1", "f1", 1)

        outcome = await orchestrator.recognize_async(request, get_current)
        assert outcome.is_stale

    @pytest.mark.asyncio
    async def test_stale_different_revision(self) -> None:
        engine = FakeOcrEngine()
        orchestrator = RecognitionOrchestrator(engine)
        request = _make_request()

        def get_current() -> SessionIdentity:
            return SessionIdentity("s1", "r1", "f1", 2)

        outcome = await orchestrator.recognize_async(request, get_current)
        assert outcome.is_stale

    @pytest.mark.asyncio
    async def test_rejected_frame_id_mismatch(self) -> None:
        engine = FakeOcrEngine()
        orchestrator = RecognitionOrchestrator(engine)
        request = RecognitionRequest(
            session_id="s1",
            request_id="r1",
            frame_id="f1",
            frame_revision=1,
            region_of_interest=ImageRect(0, 0, 100, 100),
            image=_make_frame("f2"),
        )

        def get_current() -> SessionIdentity:
            return SessionIdentity("s1", "r1", "f1", 1)

        outcome = await orchestrator.recognize_async(request, get_current)
        assert outcome.is_rejected
        assert "frame_id" in outcome.reason

    @pytest.mark.asyncio
    async def test_rejected_invalid_image(self) -> None:
        engine = FakeOcrEngine()
        orchestrator = RecognitionOrchestrator(engine)
        request = RecognitionRequest(
            session_id="s1",
            request_id="r1",
            frame_id="",
            frame_revision=1,
            region_of_interest=ImageRect(0, 0, 100, 100),
            image=ImageFrame(
                frame_id="",
                width=100,
                height=100,
                stride=300,
                pixel_format="RGB24",
                pixels=b"\x00" * (300 * 100),
                captured_at=datetime.now(timezone.utc),
            ),
        )

        def get_current() -> SessionIdentity:
            return SessionIdentity("s1", "r1", "", 1)

        outcome = await orchestrator.recognize_async(request, get_current)
        assert outcome.is_rejected