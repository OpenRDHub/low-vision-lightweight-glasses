"""CancellationToken 测试。"""

from __future__ import annotations

import asyncio

import pytest

from albassist.infrastructure.threading.cancel_token import CancellationToken


class TestCancellationToken:
    def test_initial_state(self) -> None:
        token = CancellationToken()
        assert not token.is_cancelled

    def test_cancel(self) -> None:
        token = CancellationToken()
        token.cancel()
        assert token.is_cancelled

    def test_reset(self) -> None:
        token = CancellationToken()
        token.cancel()
        token.reset()
        assert not token.is_cancelled

    @pytest.mark.asyncio
    async def test_throw_if_cancelled(self) -> None:
        token = CancellationToken()
        token.cancel()
        with pytest.raises(asyncio.CancelledError):
            await token.throw_if_cancelled_async()

    @pytest.mark.asyncio
    async def test_throw_if_not_cancelled(self) -> None:
        token = CancellationToken()
        await token.throw_if_cancelled_async()