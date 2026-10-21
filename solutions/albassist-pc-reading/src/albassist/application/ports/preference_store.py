"""偏好存储端口。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from albassist.domain.models.user_preference import UserPreference, UserPreset


@runtime_checkable
class IUserPreferenceStore(Protocol):
    """偏好存储端口。"""

    async def load_async(
        self,
        key: str,
        cancel_token: object | None = None,
    ) -> UserPreference | None: ...

    async def save_async(
        self,
        preference: UserPreference,
        cancel_token: object | None = None,
    ) -> None: ...

    async def load_all_async(
        self,
        cancel_token: object | None = None,
    ) -> dict[str, str]: ...

    async def list_presets_async(
        self,
        cancel_token: object | None = None,
    ) -> list[UserPreset]: ...

    async def save_preset_async(
        self,
        preset: UserPreset,
        cancel_token: object | None = None,
    ) -> UserPreset: ...

    async def delete_preset_async(
        self,
        preset_id: int,
        cancel_token: object | None = None,
    ) -> None: ...