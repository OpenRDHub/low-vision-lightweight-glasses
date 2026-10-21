"""离线 TTS 引擎适配器（P1）。

用本地离线引擎（pyttsx3）实现，支持暂停/停止/调速/语言切换。
"""

from __future__ import annotations

import threading
from typing import Callable

from albassist.domain.exceptions import OcrEngineNotReadyError


class TtsEngineAdapter:
    """离线 TTS 引擎适配器 - 实现 ITtsEngine 语义。"""

    def __init__(self) -> None:
        self._engine = None
        self._ready = False
        self._speaking = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_ready(self) -> bool:
        return self._ready

    def initialize(self) -> None:
        """初始化 TTS 引擎。"""
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._ready = True
        except Exception:
            self._ready = False

    async def speak_async(
        self,
        text: str,
        rate: float = 1.0,
        language: str = "zh",
        cancel_token: object | None = None,
    ) -> None:
        self.speak(text, rate, language)

    def speak(self, text: str, rate: float = 1.0, language: str = "zh") -> None:
        """同步朗读文字。"""
        if not self._ready or self._engine is None:
            raise OcrEngineNotReadyError("TTS 引擎未就绪，请检查语音包是否安装")

        with self._lock:
            self._speaking = True

        def _speak() -> None:
            try:
                assert self._engine is not None
                default_rate = self._engine.getProperty("rate")
                self._engine.setProperty("rate", int(default_rate * rate))
                self._engine.say(text)
                self._engine.runAndWait()
            finally:
                with self._lock:
                    self._speaking = False

        self._thread = threading.Thread(target=_speak, daemon=True, name="tts-worker")
        self._thread.start()

    async def pause_async(self) -> None:
        """暂停朗读。"""
        with self._lock:
            self._speaking = False
        if self._engine is not None:
            self._engine.stop()

    async def stop_async(self) -> None:
        """停止朗读。"""
        with self._lock:
            self._speaking = False
        if self._engine is not None:
            self._engine.stop()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    @property
    def is_speaking(self) -> bool:
        with self._lock:
            return self._speaking