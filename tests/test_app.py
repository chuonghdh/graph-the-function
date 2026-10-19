"""Smoke test giao diện Streamlit bằng ``AppTest``, không cần mở trình duyệt.

Các ô nhập nằm ở thanh bên với khóa ``eq_0``, ``eq_1``, ``eq_2``. Không còn nút chọn chế độ:
các test kiểm tra badge để biết hệ thống đã tự nhận diện 2D hay 3D.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT_SECONDS = 60


def _run_app() -> AppTest:
    """Khởi tạo và chạy ứng dụng với trạng thái mặc định."""
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT_SECONDS)
    at.run()
    return at


def _set_equation(at: AppTest, index: int, text: str) -> None:
    """Đặt nội dung một ô nhập ở thanh bên và chạy lại ứng dụng."""
    at.text_input(key=f"eq_{index}").input(text).run()


def _add_slot(at: AppTest) -> None:
    """Bấm nút thêm hàm số ở thanh bên, để có thêm một ô nhập."""
    at.button(key="add_slot").click().run()


def _badge_texts(at: AppTest) -> list[str]:
    """Các đoạn Markdown chứa badge tự nhận diện."""
    return [m.value for m in at.markdown if "TỰ ĐỘNG DETECT" in m.value]


def test_default_app_detects_2d() -> None:
    """Mặc định hai hàm 2D: badge 2D, có đồ thị, không lỗi."""
    at = _run_app()
    assert not at.exception
    assert len(at.error) == 0
    assert len(at.get("plotly_chart")) == 1
    assert any("Chế độ Đồ thị 2D" in t for t in _badge_texts(at))


def test_default_app_shows_intersection_table() -> None:
    """Mặc định có x² - 2 và sin(x) nên bảng giao điểm có dữ liệu."""
    at = _run_app()
    assert len(at.dataframe) == 1


def test_adding_z_function_switches_to_3d() -> None:
    """Gõ một hàm có z vào ô thứ ba, toàn bộ hệ thống tự chuyển sang 3D."""
    at = _run_app()
    _add_slot(at)
    _set_equation(at, 2, "z = x*y")
    assert not at.exception
    assert any("Chế độ Đồ thị 3D" in t for t in _badge_texts(at))
    assert len(at.get("plotly_chart")) == 1


def test_3d_scene_reports_pairwise_intersections() -> None:
    """Cảnh 3D báo cáo kết quả giao nhau cho từng cặp phương trình."""
    at = _run_app()
    _set_equation(at, 0, "x^2 + y^2 + z^2 = 16")
    _set_equation(at, 1, "z = x + y")
    assert not at.exception
    lines = [m.value for m in at.markdown if "f1 ∩ f2" in m.value]
    assert lines, "cần có dòng thông báo cho cặp f1 ∩ f2"
    assert all("tô sáng" not in line for line in lines)


def test_implicit_circle_in_2d_renders() -> None:
    """Phương trình đường tròn ẩn không cần chọn chế độ, vẫn vẽ trong 2D."""
    at = _run_app()
    _set_equation(at, 0, "x^2 + y^2 = 25")
    assert not at.exception
    assert any("Chế độ Đồ thị 2D" in t for t in _badge_texts(at))
    assert len(at.get("plotly_chart")) == 1


def test_missing_multiplication_hint_in_correct_box() -> None:
    """Gõ ``xy = 1`` báo lỗi ở đúng ô và gợi ý viết ``x*y``."""
    at = _run_app()
    _set_equation(at, 1, "xy = 1")
    assert not at.exception
    assert len(at.error) == 1
    assert "f2" in at.error[0].value
    assert "x*y" in at.error[0].value


def test_invalid_relation_is_reported_in_correct_box() -> None:
    """Bất đẳng thức bị từ chối bằng thông báo tiếng Việt ở đúng ô."""
    at = _run_app()
    _set_equation(at, 1, "x <= 2")
    assert not at.exception
    assert len(at.error) == 1
    assert "f2" in at.error[0].value
    assert "Bất đẳng thức" in at.error[0].value


def test_z_typo_still_switches_to_3d_and_reports_box() -> None:
    """Ô có z nhưng viết sai vẫn đưa hệ thống sang 3D và báo lỗi đúng ô."""
    at = _run_app()
    _add_slot(at)
    _set_equation(at, 2, "z = x**2 + ")
    assert not at.exception
    assert any("Chế độ Đồ thị 3D" in t for t in _badge_texts(at))
    assert len(at.error) == 1
    assert "f3" in at.error[0].value


def test_all_empty_shows_hint_without_crash() -> None:
    """Khi cả ba ô đều rỗng, ứng dụng yêu cầu người dùng nhập và không lỗi."""
    at = _run_app()
    for index in range(2):
        _set_equation(at, index, "")
    assert not at.exception
    assert len(at.info) >= 1


def test_y_auto_checkbox_can_be_turned_off() -> None:
    """Tắt khung y tự động vẫn vẽ được, dùng khoảng trục y đã chọn."""
    at = _run_app()
    at.checkbox(key="y_auto").uncheck().run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 1


def test_add_and_remove_slots_within_limits() -> None:
    """Thêm đến tối đa 6 ô, xóa về tối thiểu 2 ô, không vượt giới hạn."""
    at = _run_app()
    for _ in range(4):
        _add_slot(at)
    assert not at.exception
    assert at.button(key="add_slot").disabled is True
    assert all(at.text_input(key=f"eq_{i}") is not None for i in range(6))
    for slot in (2, 3, 4, 5):
        at.button(key=f"del_{slot}").click().run()
    assert not at.exception
    assert at.button(key="del_0").disabled is True
    assert at.button(key="add_slot").disabled is False


def test_six_functions_produce_fifteen_pairs_without_error() -> None:
    """Sáu hàm cho 15 cặp; mọi cặp có kết quả hoặc dòng 'không có giao điểm', không lỗi."""
    at = _run_app()
    for _ in range(4):
        _add_slot(at)
    for i, text in enumerate(["x^2 - 2", "sin(x)", "x + 1", "cos(x)", "|x| - 2", "e**(-x**2)"]):
        _set_equation(at, i, text)
    assert not at.exception
    assert len(at.error) == 0
    assert len([c for c in at.checkbox if c.key.startswith("highlight::")]) == 15


def test_abs_pi_e_inputs_render() -> None:
    """Các cú pháp |x|, pi, e chạy được trong giao diện."""
    at = _run_app()
    _set_equation(at, 0, "|x| - 1")
    _set_equation(at, 1, "sin(pi*x)")
    assert not at.exception
    assert len(at.error) == 0


def test_axis_ranges_are_number_inputs_not_sliders() -> None:
    """Mỗi trục có hai ô nhập số min và max, không còn thanh trượt."""
    at = _run_app()
    for axis in ("x_range", "y_range", "z_range"):
        assert at.number_input(key=f"{axis}_min").value is not None
        assert at.number_input(key=f"{axis}_max").value is not None


def test_invalid_range_is_reported_and_nothing_is_drawn() -> None:
    """min không nhỏ hơn max: báo lỗi, không vẽ đồ thị 2D."""
    at = _run_app()
    # Khung x tự canh sẽ bỏ qua ô nhập, nên tắt tự canh trước rồi đặt min vượt max (6).
    at.checkbox(key="x_auto").uncheck().run()
    at.number_input(key="x_range_min").set_value(7.0).run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 0
    assert any("cận min phải nhỏ hơn cận max" in e.value for e in at.error)


def test_z_range_does_not_block_2d() -> None:
    """Trục z không hợp lệ không chặn đồ thị 2D, vì 2D không dùng z."""
    at = _run_app()
    at.number_input(key="z_range_min").set_value(5.0).run()
    assert not at.exception
    assert len(at.get("plotly_chart")) == 1
