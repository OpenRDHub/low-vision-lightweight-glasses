"""SQLite 偏好存储适配器。

用 sqlite3（WAL 模式）建 preferences/presets 表，
仅存偏好不存图像/OCR 正文/阅读历史。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from albassist.domain.exceptions import PreferenceStoreError
from albassist.domain.models.user_preference import UserPreference, UserPreset


_CREATE_PREFERENCES = """
CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

_CREATE_PRESETS = """
CREATE TABLE IF NOT EXISTS presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


class SqlitePreferenceStore:
    """SQLite 偏好存储适配器。"""

    def __init__(self, db_path: str = "albassist_preferences.db") -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        try:
            self._conn = sqlite3.connect(
                self._db_path,
                isolation_level=None,
                check_same_thread=False,
            )
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute(_CREATE_PREFERENCES)
            self._conn.execute(_CREATE_PRESETS)
        except sqlite3.Error as e:
            raise PreferenceStoreError(f"数据库初始化失败: {e}") from e

    async def load_async(
        self,
        key: str,
        cancel_token: object | None = None,
    ) -> UserPreference | None:
        with self._lock:
            try:
                assert self._conn is not None
                cursor = self._conn.execute(
                    "SELECT key, value, updated_at FROM preferences WHERE key = ?",
                    (key,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                return UserPreference(
                    key=row[0],
                    value=row[1],
                    updated_at=datetime.fromisoformat(row[2]),
                )
            except sqlite3.Error as e:
                raise PreferenceStoreError(f"读取偏好失败: {e}") from e

    async def save_async(
        self,
        preference: UserPreference,
        cancel_token: object | None = None,
    ) -> None:
        with self._lock:
            try:
                assert self._conn is not None
                self._conn.execute("BEGIN IMMEDIATE")
                self._conn.execute(
                    "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
                    (
                        preference.key,
                        preference.value,
                        preference.updated_at.isoformat(),
                    ),
                )
                self._conn.execute("COMMIT")
            except sqlite3.Error as e:
                if self._conn is not None:
                    self._conn.execute("ROLLBACK")
                raise PreferenceStoreError(f"保存偏好失败: {e}") from e

    async def load_all_async(
        self,
        cancel_token: object | None = None,
    ) -> dict[str, str]:
        with self._lock:
            try:
                assert self._conn is not None
                cursor = self._conn.execute("SELECT key, value FROM preferences")
                return {row[0]: row[1] for row in cursor.fetchall()}
            except sqlite3.Error as e:
                raise PreferenceStoreError(f"读取所有偏好失败: {e}") from e

    async def list_presets_async(
        self,
        cancel_token: object | None = None,
    ) -> list[UserPreset]:
        with self._lock:
            try:
                assert self._conn is not None
                cursor = self._conn.execute(
                    "SELECT id, name, config_json, created_at FROM presets ORDER BY name"
                )
                return [
                    UserPreset(
                        id=row[0],
                        name=row[1],
                        config_json=row[2],
                        created_at=datetime.fromisoformat(row[3]),
                    )
                    for row in cursor.fetchall()
                ]
            except sqlite3.Error as e:
                raise PreferenceStoreError(f"读取预设失败: {e}") from e

    async def save_preset_async(
        self,
        preset: UserPreset,
        cancel_token: object | None = None,
    ) -> UserPreset:
        with self._lock:
            try:
                assert self._conn is not None
                now = datetime.now(timezone.utc).isoformat()
                if preset.id is None:
                    cursor = self._conn.execute(
                        "INSERT INTO presets (name, config_json, created_at) VALUES (?, ?, ?)",
                        (preset.name, preset.config_json, now),
                    )
                    return UserPreset(
                        id=cursor.lastrowid,
                        name=preset.name,
                        config_json=preset.config_json,
                        created_at=datetime.fromisoformat(now),
                    )
                self._conn.execute(
                    "UPDATE presets SET name = ?, config_json = ? WHERE id = ?",
                    (preset.name, preset.config_json, preset.id),
                )
                return preset
            except sqlite3.Error as e:
                raise PreferenceStoreError(f"保存预设失败: {e}") from e

    async def delete_preset_async(
        self,
        preset_id: int,
        cancel_token: object | None = None,
    ) -> None:
        with self._lock:
            try:
                assert self._conn is not None
                self._conn.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            except sqlite3.Error as e:
                raise PreferenceStoreError(f"删除预设失败: {e}") from e

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @staticmethod
    def load_with_fallback(db_path: str) -> SqlitePreferenceStore:
        """加载数据库，损坏时回退到内存默认。"""
        try:
            return SqlitePreferenceStore(db_path)
        except PreferenceStoreError:
            return SqlitePreferenceStore(":memory:")