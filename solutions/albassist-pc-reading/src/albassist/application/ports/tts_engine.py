"""TTS 引擎端口（P1）。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ITtsEngine(Protocol):
    """离线 TTS 引擎端口。"""

    @property
    def is_ready(self) -> bool: ...

    async def speak_async(
        self,
        text: str,
        rate: float = 1.0,
        language: str = "zh",
        cancel_token: object | None = None,
    ) -> None: ...

    async def pause_async(self) -> None: ...

    async def stop_async(self) -> None: ...