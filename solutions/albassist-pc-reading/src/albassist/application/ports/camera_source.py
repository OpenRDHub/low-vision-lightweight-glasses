"""相机源端口。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from albassist.domain.models.image_frame import ImageFrame


@dataclass(frozen=True)
class CameraDevice:
    """相机设备信息。"""

    device_id: str
    name: str
    is_available: bool


@runtime_checkable
class ICameraSource(Protocol):
    """相机源端口 - 设备无关的相机帧源。"""

    async def list_async(self, cancel_token: object | None = None) -> list[CameraDevice]: ...

    async def start_async(
        self,
        device_id: str,
        on_frame: Callable[[ImageFrame], None],
        cancel_token: object | None = None,
    ) -> None: ...

    async def stop_async(self, cancel_token: object | None = None) -> None: ...

    async def aclose(self) -> None: ...
    def set_error_callback(self, on_error: Callable[[str], None]) -> None: ...