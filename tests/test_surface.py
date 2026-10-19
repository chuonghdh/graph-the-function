"""Unit test cho ``graph_app.surface``: lưới, mặt Z và đường giao hai mặt."""

from __future__ import annotations

import numpy as np
import pytest

from graph_app.math_engine import ExpressionError, parse_expression
from graph_app.surface import (
    MAX_RESOLUTION,
    Surface,
    evaluate_surface,
    intersection_curves,
    make_grid,
)

XY = ("x", "y")


def _surface(text: str, xs: np.ndarray, ys: np.ndarray) -> Surface:
    """Tạo một ``Surface`` từ biểu thức hai biến trên lưới cho trước."""
    func = parse_expression(text, variables=XY)
    return Surface(label=text, xs=xs, ys=ys, zs=evaluate_surface(func, xs, ys))


class TestParseTwoVariables:
    """Kiểm tra bộ phân tích khi có hai biến x và y."""

    def test_evaluates_with_two_arguments(self) -> None:
        """Hàm hai biến nhận đúng hai đối số theo thứ tự ``(x, y)``."""
        func = parse_expression("x^2 + y^2", variables=XY)
        assert func(3.0, 4.0) == pytest.approx(25.0)

    def test_broadcasts_arrays(self) -> None:
        """Mảng x và y được broadcast với nhau khi tính."""
        func = parse_expression("x*y", variables=XY)
        result = func(np.array([1.0, 2.0]), np.array([[3.0], [4.0]]))
        assert result.shape == (2, 2)
        np.testing.assert_allclose(result, [[3.0, 6.0], [4.0, 8.0]])

    def test_wrong_argument_count_raises(self) -> None:
        """Gọi hàm hai biến với một đối số là lỗi lập trình, phải báo rõ ràng."""
        func = parse_expression("x*y", variables=XY)
        with pytest.raises(ValueError, match="Cần 2 đối số"):
            func(1.0)

    def test_y_rejected_in_one_variable_mode(self) -> None:
        """Chế độ 2D không cho phép biến y, nhờ vậy 2D không bị ảnh hưởng."""
        with pytest.raises(ExpressionError, match="Phát hiện thêm: y"):
            parse_expression("x*y")

    def test_unknown_variable_rejected_in_two_variable_mode(self) -> None:
        """Biến z không được hỗ trợ ngay cả khi đã bật hai biến."""
        with pytest.raises(ExpressionError):
            parse_expression("x*z", variables=XY)


class TestMakeGrid:
    """Kiểm tra tạo lưới đều."""

    def test_grid_has_requested_size_and_bounds(self) -> None:
        """Lưới có đúng số điểm và hai đầu mút trùng cận đã chọn."""
        xs, ys = make_grid((-2.0, 2.0), (0.0, 1.0), resolution=5)
        assert xs.tolist() == pytest.approx([-2.0, -1.0, 0.0, 1.0, 2.0])
        assert ys.tolist() == pytest.approx([0.0, 0.25, 0.5, 0.75, 1.0])

    @pytest.mark.parametrize(
        ("x_range", "y_range", "resolution"),
        [
            ((1.0, 1.0), (0.0, 1.0), 10),
            ((0.0, 1.0), (2.0, -2.0), 10),
            ((0.0, 1.0), (0.0, 1.0), 1),
            ((0.0, 1.0), (0.0, 1.0), MAX_RESOLUTION + 1),
        ],
    )
    def test_invalid_grid_raises(self, x_range: tuple[float, float], y_range: tuple[float, float], resolution: int) -> None:
        """Khoảng rỗng, đảo ngược hoặc độ phân giải ngoài giới hạn đều bị từ chối."""
        with pytest.raises(ValueError):
            make_grid(x_range, y_range, resolution)


class TestEvaluateSurface:
    """Kiểm tra tính mặt Z trên lưới."""

    def test_matrix_orientation_matches_grid(self) -> None:
        """Z[j, i] phải bằng f(xs[i], ys[j]), đúng quy ước của Plotly."""
        xs = np.array([0.0, 1.0, 2.0])
        ys = np.array([10.0, 20.0])
        z = evaluate_surface(parse_expression("x + y", variables=XY), xs, ys)
        assert z.shape == (2, 3)
        assert z[1, 2] == pytest.approx(22.0)
        assert z[0, 0] == pytest.approx(10.0)

    def test_undefined_points_are_nan(self) -> None:
        """Chia cho 0 và căn của số âm trở thành NaN, không ném ngoại lệ."""
        xs = np.linspace(-1.0, 1.0, 5)
        ys = np.linspace(-1.0, 1.0, 5)
        z = evaluate_surface(parse_expression("sqrt(x) + 1/y", variables=XY), xs, ys)
        assert np.isnan(z[0, 0])
        assert np.isnan(z[2, 2])

    def test_one_variable_function_is_rejected(self) -> None:
        """Hàm một biến không dùng được cho mặt 3D."""
        with pytest.raises(ValueError, match="đúng hai biến"):
            evaluate_surface(parse_expression("x"), np.zeros(2), np.zeros(2))


class TestIntersectionCurves:
    """Kiểm tra tìm đường giao giữa hai mặt."""

    def test_plane_meets_paraboloid_in_a_closed_curve(self) -> None:
        """Mặt z = x²+y² cắt mặt phẳng z = 4 theo đường tròn bán kính 2."""
        xs = np.linspace(-3.0, 3.0, 121)
        ys = np.linspace(-3.0, 3.0, 121)
        func = parse_expression("x^2 + y^2", variables=XY)
        a = _surface("x^2 + y^2", xs, ys)
        b = _surface("4", xs, ys)
        curves = intersection_curves(a, b, func)
        assert len(curves) == 1
        points = curves[0].points
        radii = np.hypot(points[:, 0], points[:, 1])
        np.testing.assert_allclose(radii, 2.0, atol=0.05)
        np.testing.assert_allclose(points[:, 2], 4.0, atol=0.05)

    def test_curve_points_lie_on_first_surface(self) -> None:
        """Mỗi điểm của đường giao phải nằm trên mặt thứ nhất: z = f(x, y)."""
        xs = np.linspace(-3.0, 3.0, 81)
        ys = np.linspace(-3.0, 3.0, 81)
        func = parse_expression("sin(sqrt(x^2 + y^2))", variables=XY)
        a = _surface("sin(sqrt(x^2 + y^2))", xs, ys)
        b = _surface("0.3*x + 0.1*y", xs, ys)
        curves = intersection_curves(a, b, func)
        assert curves
        for curve in curves:
            p = curve.points
            np.testing.assert_allclose(p[:, 2], func(p[:, 0], p[:, 1]), atol=1e-9)
            # Trên đường giao, hai mặt phải bằng nhau. Sai số từ nội suy lưới là chấp nhận được.
            np.testing.assert_allclose(p[:, 2], 0.3 * p[:, 0] + 0.1 * p[:, 1], atol=5e-3)

    def test_parallel_planes_have_no_intersection(self) -> None:
        """Hai mặt phẳng song song không cắt nhau."""
        xs = np.linspace(-1.0, 1.0, 21)
        ys = np.linspace(-1.0, 1.0, 21)
        func = parse_expression("x + y", variables=XY)
        curves = intersection_curves(_surface("x + y", xs, ys), _surface("x + y + 1", xs, ys), func)
        assert curves == []

    def test_identical_surfaces_return_empty(self) -> None:
        """Hai mặt trùng nhau không có đường giao rời rạc, trả về rỗng."""
        xs = np.linspace(-1.0, 1.0, 11)
        ys = np.linspace(-1.0, 1.0, 11)
        func = parse_expression("x*y", variables=XY)
        assert intersection_curves(_surface("x*y", xs, ys), _surface("x*y", xs, ys), func) == []

    def test_different_grids_raise(self) -> None:
        """Hai mặt phải cùng lưới, nếu không so sánh là vô nghĩa."""
        func = parse_expression("x", variables=XY)
        a = _surface("x", np.linspace(0, 1, 5), np.linspace(0, 1, 5))
        b = _surface("x", np.linspace(0, 1, 6), np.linspace(0, 1, 5))
        with pytest.raises(ValueError, match="cùng một lưới"):
            intersection_curves(a, b, func)
