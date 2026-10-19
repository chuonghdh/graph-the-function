"""Tính toán lại theo khung nhìn: miền mở rộng, mật độ thích nghi, và lọc giao điểm trong khung."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from graph_app.viewport import FIT_MIN_SPAN, PADDING, domain_for, fit_view, samples_for


def test_domain_extends_view_on_both_sides() -> None:
    """Miền tính toán rộng gấp ba khung nhìn khi PADDING = 1."""
    low, high = domain_for((-6.0, 6.0))
    assert low == pytest.approx(-6.0 - PADDING * 12.0)
    assert high == pytest.approx(6.0 + PADDING * 12.0)
    assert (high - low) == pytest.approx(3 * 12.0)


def test_sampling_density_stays_roughly_constant_on_zoom_in() -> None:
    """Zoom in vào khoảng hẹp vẫn có đủ điểm: mật độ không tụt xuống dưới mức tối thiểu."""
    narrow = samples_for(0.6, density=300.0, minimum=1500, maximum=8000)
    wide = samples_for(36.0, density=300.0, minimum=1500, maximum=8000)
    assert narrow >= 1500
    assert wide == 8000
    assert narrow / 0.6 > wide / 36.0


def test_sampling_is_capped_when_zooming_far_out() -> None:
    """Zoom out rất xa không làm số điểm vượt giới hạn trên."""
    assert samples_for(1e6, density=300.0, minimum=1500, maximum=8000) == 8000


def _app() -> AppTest:
    """Ứng dụng với mặc định hai hàm: x² - 2 và sin(x)."""
    app = str(Path(__file__).resolve().parents[1] / "app.py")
    return AppTest.from_file(app, default_timeout=120).run()


def test_curves_are_computed_beyond_the_visible_window() -> None:
    """Đường y = sin(x) có dữ liệu ra ngoài khung x [-6, 6]: zoom out vẫn có nhánh tiếp theo."""
    from graph_app.equations import parse_user_equation
    from graph_app.ui_2d import _build_curves

    equations = {1: parse_user_equation("sin(x)")}
    domain = domain_for((-6.0, 6.0))
    (curve,) = _build_curves(equations, domain, domain)
    finite_x = curve.x[np.isfinite(curve.x)]
    assert finite_x.min() < -6.0 and finite_x.max() > 6.0


def test_intersections_outside_the_view_are_not_listed() -> None:
    """Giao điểm nằm ngoài khung nhìn không xuất hiện trong bảng và không có nhãn."""
    at = _app()
    at.text_input(key="eq_0").input("x^2 - 40").run()
    assert not at.exception
    # x² - 40 = 0 có nghiệm x = ±√40 ≈ ±6.32, nằm ngoài khung [-6, 6].
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    labels = [a["text"] for a in spec["layout"].get("annotations", [])]
    assert not any("6.3245" in text or "-6.3245" in text for text in labels)


def test_auto_y_frame_ignores_data_outside_the_view() -> None:
    """Khung y tự động chỉ phụ thuộc phần đồ thị trong khung x, không bị đẩy bởi dữ liệu ngoài."""
    at = _app()
    # Tắt tự canh x và đặt khung x về [-6, 6] để kiểm tra đúng trường hợp dữ liệu ngoài khung bị loại.
    at.checkbox(key="x_auto").uncheck().run()
    at.number_input(key="x_range_min").set_value(-6.0).run()
    at.number_input(key="x_range_max").set_value(6.0).run()
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    low, high = spec["layout"]["yaxis"]["range"]
    # sin(x) và x² - 2 trong [-6, 6] có giá trị từ -2 đến 34; dữ liệu x² ngoài [-6,6] (tới 16²) bị loại khỏi khung.
    assert high < 40.0
    assert low < 0.0


def test_fit_view_contains_every_intersection() -> None:
    """Khung canh theo giao điểm phải chứa cả đầu mút trái và phải, kể cả khi có đệm."""
    low, high = fit_view([-6.5597, 2.5235], fallback=(-6.0, 6.0))
    assert low < -6.5597 and high > 2.5235


def test_fit_view_has_minimum_span_for_close_points() -> None:
    """Một giao điểm hoặc vài điểm sát nhau vẫn được khung rộng ít nhất FIT_MIN_SPAN."""
    low, high = fit_view([1.0, 1.01], fallback=(-6.0, 6.0))
    assert high - low == pytest.approx(FIT_MIN_SPAN)
    assert low < 1.0 and high > 1.01


def test_fit_view_uses_fallback_without_intersections() -> None:
    """Không có giao điểm thì khung là khoảng dự phòng."""
    assert fit_view([], fallback=(-6.0, 6.0)) == (-6.0, 6.0)


def _set_equations(at: AppTest, first: str, second: str) -> AppTest:
    """Điền hai phương trình vào ô 0 và 1, rồi chạy lại ứng dụng."""
    at.text_input(key="eq_0").input(first).run()
    at.text_input(key="eq_1").input(second).run()
    return at


def test_two_intersections_are_both_shown_with_default_frame() -> None:
    """y = x² + 4x - 15 và y = x·sin(x): khung tự canh phải chứa cả hai giao điểm (-6.5597 và 2.5235)."""
    at = _set_equations(_app(), "x^2 + 4*x - 15", "x*sin(x)")
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    labels = " ".join(a["text"] for a in spec["layout"].get("annotations", []))
    assert "-6.5597" in labels and "2.5235" in labels
    low, high = spec["layout"]["xaxis"]["range"]
    assert low < -6.5597 and high > 2.5235


def test_auto_y_frame_keeps_intersections_above_the_manual_range() -> None:
    """Khung y tự canh không được lọc giao điểm theo khoảng y mặc định (-6, 6).

    x² - 2 và y = 20 cắt nhau tại x = ±√22, tung độ 20 nằm ngoài [-6, 6] nhưng phải được hiển thị.
    """
    at = _set_equations(_app(), "x^2 - 2", "20")
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    labels = " ".join(a["text"] for a in spec["layout"].get("annotations", []))
    assert "20.0000" in labels
    _, high = spec["layout"]["yaxis"]["range"]
    assert high > 20.0


def test_intersection_at_x_180_is_framed_and_drawn() -> None:
    """Khung tự canh theo cửa sổ ±200: giao điểm tại x = 180 phải nằm trong khung và có nhãn."""
    at = _set_equations(_app(), "x", "180")
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    labels = " ".join(a["text"] for a in spec["layout"].get("annotations", []))
    assert "180.0000" in labels
    low, high = spec["layout"]["xaxis"]["range"]
    assert low < 180.0 < high


def test_identical_functions_report_no_intersection_and_do_not_frame() -> None:
    """Hai hàm trùng nhau có vô số giao điểm: không liệt kê, không dùng để canh khung, không lỗi."""
    at = _set_equations(_app(), "x", "x")
    assert not at.exception
    assert len(at.error) == 0
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    assert not spec["layout"].get("annotations")
    low, high = spec["layout"]["xaxis"]["range"]
    assert (low, high) == pytest.approx((-6.0, 6.0))


def test_many_intersections_do_not_flood_the_page() -> None:
    """sin(60x) và 0.2 cắt nhau khoảng 7600 lần trên ±200: không gắn nhãn, không lập bảng, không lỗi."""
    at = _set_equations(_app(), "sin(60*x)", "0.2")
    assert not at.exception
    assert len(at.error) == 0
    assert any("quá nhiều để hiển thị" in c.value for c in at.caption)
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    assert not spec["layout"].get("annotations")


def test_auto_y_frame_is_not_cut_for_implicit_curves() -> None:
    """x² + y² = 2500 (bán kính 50) và y = 0: khung y tự canh phải bao trọn đường tròn, không cắt phẳng ở ±18."""
    at = _set_equations(_app(), "x^2 + y^2 = 2500", "0")
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    low, high = spec["layout"]["yaxis"]["range"]
    assert high > 50.0 and low < -50.0
