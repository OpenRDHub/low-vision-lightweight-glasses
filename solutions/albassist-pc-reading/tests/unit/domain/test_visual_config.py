"""VisualConfig 模型测试。"""

from __future__ import annotations

import pytest

from albassist.domain.exceptions import VisualConfigValidationError
from albassist.domain.models.visual_config import VisualConfig, VisualMode


class TestVisualConfig:
    def test_default_config(self) -> None:
        config = VisualConfig()
        assert config.zoom_factor == 1.0
        assert config.visual_mode == VisualMode.ORIGINAL
        assert config.contrast_level == 1.0
        assert config.font_size == 48
        assert config.line_spacing == 1.5
        assert not config.eye_care

    def test_reset(self) -> None:
        config = VisualConfig.reset()
        assert config == VisualConfig()

    def test_zoom_out_of_range(self) -> None:
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(zoom_factor=0.5)
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(zoom_factor=9.0)

    def test_contrast_out_of_range(self) -> None:
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(contrast_level=-0.1)
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(contrast_level=2.1)

    def test_non_finite_values(self) -> None:
        with pytest.raises(VisualConfigValidationError, match="有限"):
            VisualConfig(zoom_factor=float("nan"))
        with pytest.raises(VisualConfigValidationError, match="有限"):
            VisualConfig(contrast_level=float("inf"))

    def test_binarize_threshold_out_of_range(self) -> None:
        with pytest.raises(VisualConfigValidationError, match="binarize_threshold"):
            VisualConfig(binarize_threshold=-1.0)
        with pytest.raises(VisualConfigValidationError, match="binarize_threshold"):
            VisualConfig(binarize_threshold=256.0)

    def test_colors_must_not_be_blank(self) -> None:
        with pytest.raises(VisualConfigValidationError, match="颜色"):
            VisualConfig(text_color=" ")
        with pytest.raises(VisualConfigValidationError, match="颜色"):
            VisualConfig(background_color="")

    def test_with_eye_care(self) -> None:
        config = VisualConfig().with_eye_care(True)
        assert config.eye_care
        assert not VisualConfig().eye_care

    def test_font_size_out_of_range(self) -> None:
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(font_size=23)
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(font_size=97)

    def test_line_spacing_out_of_range(self) -> None:
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(line_spacing=1.1)
        with pytest.raises(VisualConfigValidationError):
            VisualConfig(line_spacing=2.1)

    def test_with_zoom(self) -> None:
        config = VisualConfig()
        new_config = config.with_zoom(4.0)
        assert new_config.zoom_factor == 4.0
        assert config.zoom_factor == 1.0

    def test_with_mode(self) -> None:
        config = VisualConfig()
        new_config = config.with_mode(VisualMode.GRAYSCALE)
        assert new_config.visual_mode == VisualMode.GRAYSCALE

    def test_with_font_size(self) -> None:
        config = VisualConfig()
        new_config = config.with_font_size(72)
        assert new_config.font_size == 72

    def test_frozen(self) -> None:
        config = VisualConfig()
        with pytest.raises(AttributeError):
            config.zoom_factor = 2.0  # type: ignore[misc]
