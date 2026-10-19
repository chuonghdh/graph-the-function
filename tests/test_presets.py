"""Kiểm tra 20 hàm số nổi tiếng: cú pháp, chiều nhận diện, có dữ liệu vẽ, và hành vi dropdown."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from graph_app.equations import parse_user_equation
from graph_app.implicit import implicit_curve_polylines, isosurface_grid
from graph_app.math_engine import sample_function
from graph_app.presets import PRESET_PLACEHOLDER, PRESETS

RANGE = (-6.0, 6.0)


def test_there_are_twenty_presets_split_ten_and_ten() -> None:
    """Đúng 20 mẫu, 10 đường 2D và 10 mặt 3D."""
    assert len(PRESETS) == 20
    assert sum(name.startswith("2D - ") for name in PRESETS) == 10
    assert sum(name.startswith("3D - ") for name in PRESETS) == 10


@pytest.mark.parametrize("name", list(PRESETS))
def test_preset_parses_without_warnings_and_has_expected_dimension(name: str) -> None:
    """Mỗi mẫu biên dịch không cảnh báo, và chiều nhận diện khớp nhóm của mẫu."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        equation = parse_user_equation(PRESETS[name])
    expected = "3d" if name.startswith("3D - ") else "2d"
    assert equation.dimension == expected


@pytest.mark.parametrize("name", [n for n in PRESETS if n.startswith("2D - ")])
def test_2d_preset_produces_plottable_data(name: str) -> None:
    """Đường 2D có điểm hữu hạn (y = f(x)) hoặc có đường mức (phương trình ẩn)."""
    equation = parse_user_equation(PRESETS[name])
    with np.errstate(all="ignore"):
        if equation.is_explicit_y:
            _, y = sample_function(equation.func, *RANGE, 1500)
            assert np.isfinite(y).sum() > 100
        else:
            assert len(implicit_curve_polylines(equation.implicit_2d, RANGE, RANGE)) >= 1


@pytest.mark.parametrize("name", [n for n in PRESETS if n.startswith("3D - ")])
def test_3d_preset_has_zero_level_or_finite_surface(name: str) -> None:
    """Mặt 3D có điểm hữu hạn; mặt ẩn đổi dấu quanh mức 0 trong lưới."""
    equation = parse_user_equation(PRESETS[name])
    xs = np.linspace(-5.0, 5.0, 31)
    if equation.is_explicit_z:
        with np.errstate(all="ignore"):
            z = equation.func(*np.meshgrid(xs, xs))
        assert np.isfinite(z).sum() > 500
    else:
        values = isosurface_grid(equation.implicit_3d, xs, xs, xs)
        assert values.min() < 0 < values.max()


def _run() -> AppTest:
    """Ứng dụng khởi động mặc định."""
    app = str(Path(__file__).resolve().parents[1] / "app.py")
    return AppTest.from_file(app, default_timeout=120).run()


def test_placeholder_is_first_option() -> None:
    """Dropdown bắt đầu ở mục placeholder, chưa điền gì."""
    at = _run()
    assert at.selectbox(key="preset_choice_0").value == PRESET_PLACEHOLDER


def test_selecting_a_2d_preset_fills_f1_and_renders() -> None:
    """Chọn một mẫu 2D: f1 được điền đúng công thức, đồ thị hiện, không lỗi."""
    name = "2D - Gaussian Curve (Đường chuông Gauss)"
    at = _run()
    at.selectbox(key="preset_choice_0").select(name).run()
    assert not at.exception
    assert at.text_input(key="eq_0").value == PRESETS[name]
    assert len(at.get("plotly_chart")) == 1
    assert len(at.error) == 0


def test_selecting_a_3d_preset_switches_scene_to_3d() -> None:
    """Chọn mặt cầu: f1 điền đúng, hệ thống tự chuyển sang 3D."""
    name = "3D - Sphere (Mặt cầu bán kính 5)"
    at = _run()
    at.selectbox(key="preset_choice_0").select(name).run()
    assert not at.exception
    assert at.text_input(key="eq_0").value == PRESETS[name]
    badges = [m.value for m in at.markdown if "TỰ ĐỘNG DETECT" in m.value]
    assert any("Chế độ Đồ thị 3D" in b for b in badges)


def test_preset_applies_to_any_slot_not_only_f1() -> None:
    """Mỗi ô có dropdown riêng: chọn mẫu ở f2 thì điền vào f2, f1 không đổi."""
    name = "2D - Gaussian Curve (Đường chuông Gauss)"
    at = _run()
    original_f1 = at.text_input(key="eq_0").value
    at.selectbox(key="preset_choice_1").select(name).run()
    assert not at.exception
    assert at.text_input(key="eq_1").value == PRESETS[name]
    assert at.text_input(key="eq_0").value == original_f1
