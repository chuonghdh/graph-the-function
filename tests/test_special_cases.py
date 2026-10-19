"""Bộ ca đặc biệt về giải tích: nghiệm bội, tiệm cận, miền xác định, tiếp xúc, trùng nhau, biên khung.

Mọi đáp số được tính tay từ công thức, không lấy từ kết quả của mã. Các ca 2D đi qua đường chạy đầy
đủ của ứng dụng (``ui_2d._pair_results``). Các ca 3D kiểm tra từng điểm của đường giao nằm trên cả
hai mặt, vì đường giao được xấp xỉ trên lưới.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from graph_app.equations import parse_user_equation
from graph_app.implicit import implicit_surface_intersection, isosurface_grid
from graph_app.math_engine import parse_expression
from graph_app.refine import isolated_tangencies
from graph_app.surface import Surface, evaluate_surface, intersection_curves, make_grid
from graph_app.ui_2d import _pair_results

WINDOW = (-10.0, 10.0)
TOL = 1e-4


def _pipeline(
    first: str,
    second: str,
    x_range: tuple[float, float] = WINDOW,
    y_range: tuple[float, float] = WINDOW,
) -> list[tuple[float, float]]:
    """Giao điểm 2D theo đường đi đầy đủ của ứng dụng, đã sắp xếp theo x."""
    equations = {0: parse_user_equation(first), 1: parse_user_equation(second)}
    points = _pair_results(equations, x_range, y_range)[0].points
    return sorted((p.x, p.y) for p in points)


def _assert_points(found: list[tuple[float, float]], expected: list[tuple[float, float]], tol: float = TOL) -> None:
    """Đúng số điểm, và mỗi điểm kỳ vọng có đúng một điểm tìm được ở gần."""
    assert len(found) == len(expected), f"found {found}, expected {expected}"
    for ex, ey in expected:
        assert any(abs(fx - ex) < tol and abs(fy - ey) < tol for fx, fy in found), (ex, ey, found)


# ---------------------------------------------------------------- 2D: tường minh, nghiệm bội, tiệm cận


class TestExplicitSpecialCases:
    """Hai hàm y = g(x): nghiệm bội, dao động, tiệm cận, miền xác định, biên khung."""

    def test_cubic_meets_line_at_three_points(self) -> None:
        """x³ = x có ba nghiệm đơn: x = -1, 0, 1."""
        _assert_points(_pipeline("y = x^3", "y = x"), [(-1.0, -1.0), (0.0, 0.0), (1.0, 1.0)])

    def test_quartic_root_of_multiplicity_four_is_one_point(self) -> None:
        """x⁴ = 0 có nghiệm bội 4 tại 0: một điểm duy nhất, không nhân đôi."""
        _assert_points(_pipeline("y = x^4", "y = 0"), [(0.0, 0.0)])

    def test_sin_x_meets_sin_2x_on_one_period(self) -> None:
        """sin x = sin 2x trên [0, 2π] ⇔ sin x (2cos x − 1) = 0: x = 0, π/3, π, 5π/3, 2π."""
        s3 = math.sqrt(3.0) / 2
        expected = [(0.0, 0.0), (math.pi / 3, s3), (math.pi, 0.0), (5 * math.pi / 3, -s3), (2 * math.pi, 0.0)]
        _assert_points(_pipeline("y = sin(x)", "y = sin(2*x)", x_range=(0.0, 2 * math.pi)), expected)

    def test_reciprocal_meets_identity_only_away_from_pole(self) -> None:
        """1/x = x có nghiệm x = ±1. Tiệm cận x = 0 đổi dấu nhưng không phải giao điểm."""
        _assert_points(_pipeline("y = 1/x", "y = x"), [(-1.0, -1.0), (1.0, 1.0)])

    def test_reciprocal_never_meets_axis(self) -> None:
        """1/x không bao giờ bằng 0. Điểm đổi dấu tại tiệm cận bị loại."""
        _assert_points(_pipeline("y = 1/x", "y = 0"), [])

    def test_sqrt_meets_linear_at_zero_and_four(self) -> None:
        """√x = x/2 ⇔ x = 0 hoặc x = 4 (bình phương: x = x²/4)."""
        _assert_points(_pipeline("y = sqrt(x)", "y = x/2"), [(0.0, 0.0), (4.0, 2.0)])

    def test_sqrt_is_undefined_on_negatives(self) -> None:
        """√x không xác định với x < 0 (miền số thực), nên không giao với y = -1."""
        _assert_points(_pipeline("y = sqrt(x)", "y = -1"), [])

    def test_log_tangent_to_line_at_one(self) -> None:
        """ln x và tiếp tuyến y = x - 1 chạm nhau tại (1, 0). Log không xác định với x ≤ 0."""
        _assert_points(_pipeline("y = log(x)", "y = x - 1"), [(1.0, 0.0)])

    def test_absolute_value_crosses_constant_twice(self) -> None:
        """|x| = 2 có hai nghiệm x = ±2."""
        _assert_points(_pipeline("y = abs(x)", "y = 2"), [(-2.0, 2.0), (2.0, 2.0)])

    def test_parallel_translates_never_meet(self) -> None:
        """y = x² và y = x² + 1 song song theo phương tung, không có điểm chung."""
        _assert_points(_pipeline("y = x^2", "y = x^2 + 1"), [])

    def test_intersection_outside_window_is_not_reported(self) -> None:
        """Parabol y = x² - 25 cắt y = 0 tại x = ±5, nhưng khung x [-3, 3] không chứa chúng."""
        _assert_points(_pipeline("y = x^2 - 25", "y = 0", x_range=(-3.0, 3.0)), [])

    def test_roots_inside_window_are_reported(self) -> None:
        """Cùng parabol, khung [-6, 6] chứa x = ±5: hai điểm."""
        _assert_points(_pipeline("y = x^2 - 25", "y = 0", x_range=(-6.0, 6.0)), [(-5.0, 0.0), (5.0, 0.0)])

    def test_identical_on_a_ray_does_not_flood_the_result(self) -> None:
        """|x| = x trên x ≥ 0 là cả một tia trùng nhau (vô số giao điểm). Không được liệt kê hàng nghìn điểm."""
        points = _pipeline("y = abs(x)", "y = x")
        assert len(points) <= 2


# ---------------------------------------------------------------- 2D: ẩn


class TestImplicitSpecialCases:
    """Đường ẩn 2D: đường tròn, elip, hypebol, đường thẳng đứng, tiếp xúc và đồng tâm."""

    def test_two_circles_meet_at_symmetric_points(self) -> None:
        """x² + y² = 5 và (x-1)² + y² = 5: x = 1/2, y = ±√(5 - 1/4)."""
        half = math.sqrt(4.75)
        _assert_points(_pipeline("x^2 + y^2 = 5", "(x-1)^2 + y^2 = 5"), [(0.5, half), (0.5, -half)])

    def test_circle_meets_hyperbola_in_four_points(self) -> None:
        """x² + y² = 4 và xy = 1: x⁴ - 4x² + 1 = 0, nên x² = 2 ± √3, y = 1/x. Bốn điểm."""
        a = math.sqrt(2.0 + math.sqrt(3.0))
        b = math.sqrt(2.0 - math.sqrt(3.0))
        expected = [(a, 1 / a), (-a, -1 / a), (b, 1 / b), (-b, -1 / b)]
        _assert_points(_pipeline("x^2 + y^2 = 4", "x*y = 1"), expected)

    def test_ellipse_tangent_to_horizontal_line_at_top(self) -> None:
        """x²/9 + y²/4 = 1 chạm y = 2 tại (0, 2)."""
        _assert_points(_pipeline("x^2/9 + y^2/4 = 1", "y = 2"), [(0.0, 2.0)])

    def test_vertical_line_meets_parabola_once(self) -> None:
        """x = 2 cắt y = x² tại (2, 4), đường thẳng đứng không phải hàm của x."""
        _assert_points(_pipeline("x = 2", "y = x^2"), [(2.0, 4.0)])

    def test_concentric_circles_never_meet(self) -> None:
        """x² + y² = 1 và x² + y² = 4 đồng tâm, không có điểm chung."""
        _assert_points(_pipeline("x^2 + y^2 = 1", "x^2 + y^2 = 4"), [])

    def test_circle_outside_window_is_not_reported(self) -> None:
        """x² + y² = 25 cắt y = 0 tại (±5, 0), khung [-3, 3]×[-10, 10] không chứa chúng."""
        _assert_points(_pipeline("x^2 + y^2 = 25", "y = 0", x_range=(-3.0, 3.0)), [])

    def test_circle_tangent_to_vertical_line(self) -> None:
        """x² + y² = 4 chạm x = 2 tại (2, 0). Đây là tiếp xúc giữa đường ẩn và đường thẳng đứng."""
        _assert_points(_pipeline("x^2 + y^2 = 4", "x = 2"), [(2.0, 0.0)])

    def test_implicit_crossing_at_origin_with_tangent_branches(self) -> None:
        """Nút x² - y² = 0 (hai nhánh qua gốc) và đường tròn x² + y² = 1 cắt nhau tại bốn điểm (±1/√2, ±1/√2)."""
        s = 1 / math.sqrt(2.0)
        _assert_points(_pipeline("x^2 - y^2 = 0", "x^2 + y^2 = 1"), [(s, s), (s, -s), (-s, s), (-s, -s)])


# ---------------------------------------------------------------- 3D: mặt tường minh


def _explicit_surface(label: str, text: str, resolution: int = 81, span: float = 3.0) -> tuple[Surface, object]:
    """Mặt z = f(x, y) trên lưới đều, cùng với hàm đã phân tích của nó."""
    xs, ys = make_grid((-span, span), (-span, span), resolution)
    func = parse_expression(text, variables=("x", "y"))
    return Surface(label=label, xs=xs, ys=ys, zs=evaluate_surface(func, xs, ys)), func


def _curve_points(first: str, second: str) -> np.ndarray:
    """Các điểm (x, y, z) của đường giao hai mặt tường minh, gộp thành một mảng."""
    surface_a, func_a = _explicit_surface("a", first)
    surface_b, func_b = _explicit_surface("b", second)
    lines = intersection_curves(surface_a, surface_b, func_a, func_b)
    return np.vstack([line.points for line in lines]) if lines else np.empty((0, 3))


class TestExplicitSurfaceCurves:
    """Đường giao của hai mặt z = f(x, y): mọi điểm phải nằm trên cả hai mặt."""

    def test_paraboloid_meets_plane_in_a_circle(self) -> None:
        """z = x² + y² cắt z = 4 tại đường tròn x² + y² = 4 ở độ cao 4."""
        points = _curve_points("x^2 + y^2", "4")
        assert points.shape[0] > 0
        radius = np.hypot(points[:, 0], points[:, 1])
        assert np.allclose(radius, 2.0, atol=1e-9)
        # Đường giao được chiếu về f₁ − f₂ = 0 bằng Gauss–Newton, nên chính xác đến sai số máy.
        assert np.allclose(points[:, 2], 4.0, atol=1e-9)

    def test_two_planes_meet_in_a_line(self) -> None:
        """z = x + y và z = 0 cắt nhau theo đường x + y = 0."""
        points = _curve_points("x + y", "0")
        assert points.shape[0] > 0
        assert np.allclose(points[:, 0] + points[:, 1], 0.0, atol=0.05)
        assert np.allclose(points[:, 2], 0.0, atol=0.05)

    def test_tangent_paraboloid_and_plane_give_no_long_curve(self) -> None:
        """z = x² + y² chạm z = 0 chỉ tại gốc. Không được có đường dài nào, chỉ có điểm sát gốc (nếu có)."""
        points = _curve_points("x^2 + y^2", "0")
        if points.shape[0]:
            assert np.hypot(points[:, 0], points[:, 1]).max() < 0.2

    def test_parallel_planes_never_meet(self) -> None:
        """z = x và z = x + 1 song song, không có đường giao."""
        assert _curve_points("x", "x + 1").shape[0] == 0

    def test_sine_surface_meets_zero_plane_on_lines(self) -> None:
        """z = sin x cắt z = 0 tại các đường x = kπ. Mọi điểm phải có sin x ≈ 0."""
        points = _curve_points("sin(x)", "0")
        assert points.shape[0] > 0
        assert np.allclose(np.sin(points[:, 0]), 0.0, atol=0.05)


# ---------------------------------------------------------------- 3D: mặt ẩn


def _implicit_grid(text: str, xs: np.ndarray, ys: np.ndarray, zs: np.ndarray) -> np.ndarray:
    """Giá trị F(x, y, z) của phương trình ẩn trên lưới 3D."""
    return isosurface_grid(parse_user_equation(text).implicit_3d, xs, ys, zs)


class TestImplicitSurfaceCurves:
    """Đường giao của hai mặt ẩn F = 0, G = 0 trên lưới: mọi đoạn phải gần cả hai mặt."""

    @pytest.fixture
    def grid(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Lưới 41³ trên [-1.5, 1.5]³, bước 0.075."""
        axis = np.linspace(-1.5, 1.5, 41)
        return axis, axis.copy(), axis.copy()

    def test_sphere_meets_plane_in_unit_circle(self, grid: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
        """x² + y² + z² = 1 cắt z = 0 tại đường tròn bán kính 1. Đầu mút đoạn gần đường tròn (sai số ≤ bước lưới)."""
        xs, ys, zs = grid
        first = parse_user_equation("x^2 + y^2 + z^2 = 1").implicit_3d
        second = parse_user_equation("z = 0").implicit_3d
        segments = implicit_surface_intersection(
            _implicit_grid("x^2 + y^2 + z^2 = 1", xs, ys, zs),
            _implicit_grid("z = 0", xs, ys, zs),
            xs,
            ys,
            zs,
            refine_with=(first, second),
        )
        assert segments.shape[0] > 0
        endpoints = segments.reshape(-1, 3)
        assert np.allclose(endpoints[:, 2], 0.0, atol=1e-9)
        assert np.allclose(np.hypot(endpoints[:, 0], endpoints[:, 1]), 1.0, atol=1e-9)

    def test_externally_tangent_spheres_touch_at_one_point(self, grid: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
        """Hai mặt cầu bán kính 1, tâm (0,0,0) và (2,0,0), chạm nhau đúng tại (1,0,0)."""
        xs, ys, zs = grid
        tangents = isolated_tangencies(
            parse_user_equation("x^2 + y^2 + z^2 = 1").implicit_3d,
            parse_user_equation("(x-2)^2 + y^2 + z^2 = 1").implicit_3d,
            xs,
            ys,
            zs,
            _implicit_grid("x^2 + y^2 + z^2 = 1", xs, ys, zs),
            _implicit_grid("(x-2)^2 + y^2 + z^2 = 1", xs, ys, zs),
        )
        assert tangents.shape == (1, 3)
        # Tiếp điểm là nghiệm kép: chính xác đến √ε ≈ 1e-8, không đến 1e-16.
        assert np.allclose(tangents[0], [1.0, 0.0, 0.0], atol=1e-6)

    def test_sphere_tangent_to_plane_at_its_top(self, grid: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
        """Mặt cầu x² + y² + z² = 1 chạm mặt phẳng z = 1 tại (0, 0, 1)."""
        xs, ys, zs = grid
        tangents = isolated_tangencies(
            parse_user_equation("x^2 + y^2 + z^2 = 1").implicit_3d,
            parse_user_equation("z = 1").implicit_3d,
            xs,
            ys,
            zs,
            _implicit_grid("x^2 + y^2 + z^2 = 1", xs, ys, zs),
            _implicit_grid("z = 1", xs, ys, zs),
        )
        assert tangents.shape == (1, 3)
        assert np.allclose(tangents[0], [0.0, 0.0, 1.0], atol=1e-6)

    def test_disjoint_spheres_have_no_intersection(self, grid: tuple[np.ndarray, np.ndarray, np.ndarray]) -> None:
        """Hai mặt cầu bán kính 1 tâm cách nhau 3 không cắt nhau."""
        xs, ys, zs = grid
        segments = implicit_surface_intersection(
            _implicit_grid("x^2 + y^2 + z^2 = 1", xs, ys, zs),
            _implicit_grid("(x-3)^2 + y^2 + z^2 = 1", xs, ys, zs),
            xs,
            ys,
            zs,
        )
        assert segments.shape[0] == 0
