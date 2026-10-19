"""Unit test cho ``graph_app.math_engine``: phân tích biểu thức, lấy mẫu và tìm giao điểm."""

from __future__ import annotations

import math
import time

import numpy as np
import pytest

from graph_app.math_engine import (
    MAX_EXPRESSION_LENGTH,
    ExpressionError,
    find_intersections,
    parse_expression,
    sample_function,
)


def _values_at(text: str, xs: list[float]) -> np.ndarray:
    """Tính giá trị của biểu thức ``text`` tại các điểm ``xs``."""
    return parse_expression(text)(np.array(xs, dtype=float))


class TestParseExpression:
    """Kiểm tra bộ phân tích biểu thức và tính giá trị."""

    @pytest.mark.parametrize(
        ("text", "x", "expected"),
        [
            ("x^2 - 2", 3.0, 7.0),
            ("x**2 + 2*x + 1", 2.0, 9.0),
            ("2x + 1", 3.0, 7.0),  # nhân ẩn
            ("sin(x)", math.pi / 2, 1.0),
            ("cos(0)", 5.0, 1.0),
            ("tan(x)", math.pi / 4, 1.0),
            ("exp(0) + e^0", 0.0, 2.0),
            ("ln(e)", 0.0, 1.0),
            ("log(x)", math.e, 1.0),  # log là logarit tự nhiên
            ("log10(1000)", 0.0, 3.0),
            ("log2(8)", 0.0, 3.0),
            ("sqrt(16)", 0.0, 4.0),
            ("abs(-3)", 0.0, 3.0),
            ("π", 0.0, math.pi),
        ],
    )
    def test_evaluates_supported_syntax(self, text: str, x: float, expected: float) -> None:
        """Các cú pháp được hỗ trợ cho kết quả đúng."""
        assert _values_at(text, [x])[0] == pytest.approx(expected)

    def test_returns_nan_outside_domain(self) -> None:
        """Căn và log của số âm, log của 0 là không xác định, trả về NaN."""
        values = _values_at("sqrt(x)", [-1.0, 4.0])
        assert math.isnan(values[0])
        assert values[1] == pytest.approx(2.0)

        assert math.isnan(_values_at("log(x)", [-1.0])[0])
        assert math.isnan(_values_at("log(x)", [0.0])[0])

    def test_division_by_zero_returns_nan(self) -> None:
        """Chia cho 0 không ném ngoại lệ mà trả về NaN, để đường vẽ bị ngắt."""
        values = _values_at("1/x", [0.0, 2.0])
        assert math.isnan(values[0])
        assert values[1] == pytest.approx(0.5)

    def test_broadcasts_constant_function(self) -> None:
        """Hàm hằng phải trả về mảng cùng kích thước với đầu vào."""
        values = _values_at("3", [0.0, 1.0, 2.0])
        assert values.shape == (3,)
        assert np.all(values == 3.0)

    def test_huge_power_does_not_hang(self) -> None:
        """Lũy thừa số lớn được đổi thành float nên không treo tiến trình."""
        started = time.perf_counter()
        values = _values_at("9**9**9", [2.0])
        assert time.perf_counter() - started < 2.0
        assert math.isinf(values[0]) or math.isnan(values[0])

    @pytest.mark.parametrize(
        "text",
        [
            "__import__('os')",
            "x.real",
            "x[0]",
            "lambda: 1",
            "Add(x, x)",
            "open('f')",
            "x_1",
            "x!",
        ],
    )
    def test_rejects_unsafe_input(self, text: str) -> None:
        """Mọi thứ ngoài cú pháp toán học thuần túy đều bị từ chối."""
        with pytest.raises(ExpressionError):
            parse_expression(text)

    def test_rejects_unknown_name(self) -> None:
        """Tên không nằm trong danh sách cho phép như ``foo`` bị từ chối."""
        with pytest.raises(ExpressionError, match="foo"):
            parse_expression("foo(x)")

    def test_rejects_other_variables(self) -> None:
        """Chỉ được dùng biến x. Biến như ``a`` hoặc ``y`` bị từ chối."""
        with pytest.raises(ExpressionError, match="Tên 'a'"):
            parse_expression("a*x")

    @pytest.mark.parametrize("text", ["", "   ", "2+", "sin(x", "x^^"])
    def test_rejects_malformed_syntax(self, text: str) -> None:
        """Biểu thức rỗng hoặc sai cú pháp báo lỗi rõ ràng."""
        with pytest.raises(ExpressionError):
            parse_expression(text)

    def test_rejects_too_long_expression(self) -> None:
        """Biểu thức vượt quá giới hạn độ dài bị từ chối."""
        with pytest.raises(ExpressionError, match="quá dài"):
            parse_expression("x+" * MAX_EXPRESSION_LENGTH)

    def test_error_is_value_error(self) -> None:
        """``ExpressionError`` là lớp con của ``ValueError`` để tương thích ngược."""
        assert issubclass(ExpressionError, ValueError)


class TestSampleFunction:
    """Kiểm tra lấy mẫu hàm số trên một khoảng."""

    def test_returns_requested_grid(self) -> None:
        """Lưới x có đúng số điểm và hai đầu mút."""
        x, y = sample_function(parse_expression("x"), -2.0, 2.0, 5)
        assert x.tolist() == pytest.approx([-2.0, -1.0, 0.0, 1.0, 2.0])
        assert y.tolist() == pytest.approx(x.tolist())

    def test_invalid_range_raises(self) -> None:
        """Khoảng rỗng hoặc đảo ngược bị từ chối."""
        with pytest.raises(ValueError):
            sample_function(parse_expression("x"), 1.0, 1.0)
        with pytest.raises(ValueError):
            sample_function(parse_expression("x"), 2.0, -2.0)

    def test_too_few_samples_raises(self) -> None:
        """Số mẫu nhỏ hơn 2 không hợp lệ."""
        with pytest.raises(ValueError):
            sample_function(parse_expression("x"), 0.0, 1.0, samples=1)


class TestFindIntersections:
    """Kiểm tra dò giao điểm giữa hai hàm số."""

    def test_quadratic_meets_line_at_two_points(self) -> None:
        """Parabol x² và đường y = 2 cắt nhau tại x = ±√2."""
        points = find_intersections(parse_expression("x^2"), parse_expression("2"), -5.0, 5.0)
        assert [p.x for p in points] == pytest.approx([-math.sqrt(2), math.sqrt(2)], abs=1e-9)
        assert [p.y for p in points] == pytest.approx([2.0, 2.0], abs=1e-9)

    def test_sine_crosses_zero_periodically(self) -> None:
        """sin(x) = 0 trên [0, 2π] có ba nghiệm: 0, π và 2π, gồm cả hai đầu mút."""
        points = find_intersections(parse_expression("sin(x)"), parse_expression("0"), 0.0, 2 * math.pi)
        assert [p.x for p in points] == pytest.approx([0.0, math.pi, 2 * math.pi], abs=1e-9)

    def test_tangency_is_detected(self) -> None:
        """Parabol x² tiếp xúc trục hoành tại 0. Đây là giao điểm dù không đổi dấu."""
        points = find_intersections(parse_expression("x^2"), parse_expression("0"), -5.0, 5.0)
        assert len(points) == 1
        assert points[0].x == pytest.approx(0.0, abs=1e-9)
        assert points[0].y == pytest.approx(0.0, abs=1e-9)

    def test_asymptote_is_not_an_intersection(self) -> None:
        """1/x và trục hoành không giao nhau. Điểm đổi dấu tại tiệm cận x=0 bị loại."""
        points = find_intersections(parse_expression("1/x"), parse_expression("0"), -5.0, 5.0)
        assert points == []

    def test_tan_asymptote_is_not_an_intersection(self) -> None:
        """tan(x) cắt trục hoành tại kπ, không cắt tại các tiệm cận π/2 + kπ."""
        points = find_intersections(parse_expression("tan(x)"), parse_expression("0"), -5.0, 5.0)
        xs = [p.x for p in points]
        assert xs == pytest.approx([-math.pi, 0.0, math.pi], abs=1e-9)

    def test_parallel_lines_have_no_intersection(self) -> None:
        """Hai đường song song không có giao điểm."""
        points = find_intersections(parse_expression("x+1"), parse_expression("x+2"), -5.0, 5.0)
        assert points == []

    def test_identical_functions_return_empty(self) -> None:
        """Hai hàm trùng nhau có vô số giao điểm, hàm trả về rỗng thay vì liệt kê hàng nghìn điểm."""
        points = find_intersections(parse_expression("x"), parse_expression("x"), -5.0, 5.0)
        assert points == []

    def test_intersection_outside_range_is_ignored(self) -> None:
        """Giao điểm nằm ngoài khoảng dò không được trả về."""
        points = find_intersections(parse_expression("x^2"), parse_expression("100"), -5.0, 5.0)
        assert points == []

    def test_y_is_computed_from_first_function(self) -> None:
        """Tung độ giao điểm được tính theo hàm thứ nhất."""
        points = find_intersections(parse_expression("x"), parse_expression("2"), 0.0, 5.0)
        assert len(points) == 1
        assert points[0].x == pytest.approx(2.0, abs=1e-9)
        assert points[0].y == pytest.approx(2.0, abs=1e-9)

    def test_results_are_sorted_and_unique(self) -> None:
        """Kết quả được sắp xếp theo x và không có điểm trùng lặp."""
        points = find_intersections(parse_expression("sin(x)"), parse_expression("0.5"), -10.0, 10.0)
        xs = [p.x for p in points]
        assert xs == sorted(xs)
        assert len(xs) == len(set(xs))

    def test_invalid_range_raises(self) -> None:
        """Khoảng dò không hợp lệ bị từ chối."""
        with pytest.raises(ValueError):
            find_intersections(parse_expression("x"), parse_expression("0"), 5.0, -5.0)

    def test_quadratic_meets_x_sin_x_at_two_points(self) -> None:
        """y = x² + 4x - 15 và y = x·sin(x) trên [-10, 10] cắt nhau đúng hai lần (đối chiếu bằng quét lưới mịn)."""
        points = find_intersections(
            parse_expression("x^2 + 4*x - 15"),
            parse_expression("x*sin(x)"),
            -10.0,
            10.0,
        )
        assert [p.x for p in points] == pytest.approx([-6.559685, 2.523526], abs=1e-6)
        assert [p.y for p in points] == pytest.approx([1.790731, 1.462284], abs=1e-6)

    def test_polynomial_double_root_is_found_exactly(self) -> None:
        """(x - 1)²·(x + 2) = 0 có nghiệm bội 2 tại x = 1 và nghiệm đơn tại x = -2, đều tính bằng SymPy.

        Dung sai 1e-7 thay vì 1e-9 vì tại nghiệm bội 2, h(1 + δ) ~ δ², nên float64 chỉ xác định
        δ tới cỡ √ε ≈ 1e-8. Đây là giới hạn của phép tính, không phải lỗi thuật toán.
        """
        points = find_intersections(parse_expression("(x-1)^2*(x+2)"), parse_expression("0"), -5.0, 5.0)
        assert [p.x for p in points] == pytest.approx([-2.0, 1.0], abs=1e-7)

    def test_reciprocal_meets_line_skipping_pole(self) -> None:
        """1/x = x có nghiệm x = ±1. Đoạn chứa tiệm cận x = 0 làm brentq gặp NaN, phải được bỏ qua mà không lỗi."""
        points = find_intersections(parse_expression("1/x"), parse_expression("x"), -5.0, 5.0)
        assert [p.x for p in points] == pytest.approx([-1.0, 1.0], abs=1e-9)

    def test_transcendental_tangency_is_detected(self) -> None:
        """cos(x) tiếp xúc y = 1 tại x = 0 mà không đổi dấu. Nhánh số phải bắt được tiếp xúc này."""
        points = find_intersections(parse_expression("cos(x)"), parse_expression("1"), -1.0, 1.0)
        assert len(points) == 1
        assert points[0].x == pytest.approx(0.0, abs=1e-6)
        assert points[0].y == pytest.approx(1.0, abs=1e-9)


class TestWideSearchWindow:
    """Dò giao điểm trên cửa sổ ±200: đáp số đối chiếu được bằng công thức, không chỉ kiểm tra không lỗi."""

    def test_sine_zeros_on_pm_200_are_all_found(self) -> None:
        """sin(x) = 0 trên [-200, 200] có đúng 127 nghiệm kπ với |k| ≤ 63 (63π ≈ 197.9 < 200 < 64π)."""
        points = find_intersections(parse_expression("sin(x)"), parse_expression("0"), -200.0, 200.0, 100_000)
        assert len(points) == 127
        assert points[0].x == pytest.approx(-63 * math.pi, abs=1e-9)
        assert points[-1].x == pytest.approx(63 * math.pi, abs=1e-9)

    def test_plateau_of_abs_difference_is_fast_and_correct(self) -> None:
        """x + 1 và |x| - 2 chỉ cắt tại x = -1.5. Đoạn x ≥ 0 có |h| = 3 không đổi, không được tạo hàng nghìn ứng viên."""
        points = find_intersections(parse_expression("x + 1"), parse_expression("|x| - 2"), -200.0, 200.0, 100_000)
        assert [p.x for p in points] == pytest.approx([-1.5], abs=1e-9)

    def test_intersection_near_the_window_edge_is_found(self) -> None:
        """y = x và y = 180 cắt nhau tại (180, 180), gần biên 200 của cửa sổ dò."""
        points = find_intersections(parse_expression("x"), parse_expression("180"), -200.0, 200.0, 100_000)
        assert [p.x for p in points] == pytest.approx([180.0], abs=1e-9)


class TestDenseAndPolynomialRegressions:
    """Hồi quy cho các lỗi tìm thấy khi rà soát độc lập: nhánh đa thức, cặp nghiệm trong một ô, tốc độ."""

    def test_polynomial_branch_is_taken_for_integer_coefficients(self) -> None:
        """x² + 4x - 15 phải đi nhánh SymPy (đa thức). Trước đây hệ số Float làm nhánh này không bao giờ chạy."""
        from graph_app.math_engine import _polynomial_difference

        assert _polynomial_difference(parse_expression("x^2 + 4*x - 15"), parse_expression("0")) is not None
        assert _polynomial_difference(parse_expression("sin(x)"), parse_expression("0")) is None

    def test_dense_zeros_of_sin_100x_are_all_found(self) -> None:
        """sin(100x) = 0 trên [-200, 200]: 12733 nghiệm kπ/100, khớp quét lưới 8 triệu điểm."""
        points = find_intersections(parse_expression("sin(100*x)"), parse_expression("0"), -200.0, 200.0, 100_000)
        assert len(points) == 12733

    def test_two_roots_inside_one_grid_cell_are_both_found(self) -> None:
        """sin(x - c + π/2) và 1 - 1.6e-6 cắt nhau tại c ± 0.0018, hai nghiệm cách nhau nhỏ hơn bước lưới 0.004.

        Đây là ca đối kháng: mọi điểm lưới đều dương, nghiệm chỉ nằm trong một ô.
        """
        step = 400.0 / 99_999
        center = -200.0 + 640.5 * step
        shift = center - math.pi / 2
        first = parse_expression(f"sin(x - {shift:.15f})")
        second = parse_expression("1 - 0.0000016")
        points = find_intersections(first, second, -200.0, 200.0, 100_000)
        xs = [p.x for p in points if abs(p.x - center) < 0.01]
        assert len(xs) == 2
        assert xs == pytest.approx([center - 0.00179, center + 0.00179], abs=2e-5)

    def test_dense_oscillating_pair_finishes_quickly(self) -> None:
        """sin(100x) và cos(x) trên [-200, 200] có 12733 giao điểm và phải xong trong 3 giây."""
        started = time.perf_counter()
        points = find_intersections(parse_expression("sin(100*x)"), parse_expression("cos(x)"), -200.0, 200.0, 100_000)
        elapsed = time.perf_counter() - started
        assert len(points) == 12733
        assert elapsed < 3.0
