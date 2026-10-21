"""ImageRect 几何模型测试。"""

from __future__ import annotations

import pytest

from albassist.domain.geometry import ImageRect


class TestImageRect:
    def test_is_empty(self) -> None:
        assert ImageRect(0, 0, 0, 100).is_empty
        assert ImageRect(0, 0, 100, 0).is_empty
        assert not ImageRect(0, 0, 100, 100).is_empty

    def test_right_bottom(self) -> None:
        rect = ImageRect(10, 20, 100, 200)
        assert rect.right == 110
        assert rect.bottom == 220

    def test_area(self) -> None:
        assert ImageRect(0, 0, 100, 200).area == 20000

    def test_clamp_to_within_bounds(self) -> None:
        rect = ImageRect(10, 10, 100, 100)
        clamped = rect.clamp_to(200, 200)
        assert clamped == rect

    def test_clamp_to_negative_origin(self) -> None:
        rect = ImageRect(-10, -10, 100, 100)
        clamped = rect.clamp_to(200, 200)
        assert clamped.x == 0
        assert clamped.y == 0
        assert clamped.width == 90
        assert clamped.height == 90

    def test_clamp_to_exceeds_bounds(self) -> None:
        rect = ImageRect(150, 150, 100, 100)
        clamped = rect.clamp_to(200, 200)
        assert clamped.x == 150
        assert clamped.y == 150
        assert clamped.width == 50
        assert clamped.height == 50

    def test_clamp_to_completely_outside(self) -> None:
        rect = ImageRect(300, 300, 100, 100)
        clamped = rect.clamp_to(200, 200)
        assert clamped.is_empty

    def test_clamp_to_zero_image(self) -> None:
        rect = ImageRect(10, 10, 100, 100)
        clamped = rect.clamp_to(0, 0)
        assert clamped.is_empty

    def test_contains(self) -> None:
        outer = ImageRect(0, 0, 100, 100)
        inner = ImageRect(10, 10, 50, 50)
        assert outer.contains(inner)
        assert not inner.contains(outer)

    def test_intersects(self) -> None:
        r1 = ImageRect(0, 0, 100, 100)
        r2 = ImageRect(50, 50, 100, 100)
        r3 = ImageRect(200, 200, 100, 100)
        assert r1.intersects(r2)
        assert not r1.intersects(r3)

    def test_frozen(self) -> None:
        rect = ImageRect(0, 0, 100, 100)
        with pytest.raises(AttributeError):
            rect.x = 10  # type: ignore[misc]