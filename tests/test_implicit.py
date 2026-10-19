"""Unit test cho ``graph_app.implicit``: đường ẩn 2D, giao điểm ẩn, mặt ẩn 3D và đường giao 3D."""

from __future__ import annotations

import math

import numpy as np
import pytest

from graph_app.equations import parse_user_equation
from graph_app.implicit import (
    find_implicit_intersections,
    implicit_curve_polylines,
    implicit_surface_intersection,
    isosurface_grid,
)
from graph_app.math_engine import ParsedFunction

RANGE = (-6.0, 6.0)


def _f2d(text: str) -> ParsedFunction:
    """Dạng ẩn ``F(x, y)`` của một phương trình, dùng cho các phép kiểm tra 2D."""
    implicit = parse_user_equation(text).implicit_2d
    assert implicit is not None, f"{text!r} không có dạng 2D"
    return implicit


def _f3d(text: str) -> ParsedFunction:
    """Dạng ẩn ``F(x, y, z)`` của một phương trình, dùng cho các phép kiểm tra 3D."""
    return parse_user_equation(text).implicit_3d


class TestImplicitCurve2D:
    """Đường mức 0 trong mặt phẳng."""

    def test_circle_points_lie_on_radius(self) -> None:
        """Mọi điểm của đường tròn bán kính 5 nằm đúng bán kính 5, sai số dưới 1e-3."""
        lines = implicit_curve_polylines(_f2d("x^2 + y^2 = 25"), RANGE, RANGE, samples=200)
        points = np.vstack(lines)
        radii = np.hypot(points[:, 0], points[:, 1])
        assert np.max(np.abs(radii - 5.0)) < 1e-3

    def test_ellipse_is_closed_curve(self) -> None:
        """Elip nằm hoàn toàn trong khung thì là một đường kín, không bị cắt."""
        lines = implicit_curve_polylines(_f2d("x^2/9 + y^2/4 = 1"), RANGE, RANGE, samples=200)
        assert len(lines) == 1
        assert np.allclose(lines[0][0], lines[0][-1], atol=0.05)

    def test_curve_outside_frame_is_empty(self) -> None:
        """Đường không đi qua khung trả về rỗng, không ném ngoại lệ."""
        assert implicit_curve_polylines(_f2d("x^2 + y^2 = 10000"), (-1, 1), (-1, 1)) == []

    def test_invalid_range_raises(self) -> None:
        """Khoảng đảo ngược bị từ chối."""
        with pytest.raises(ValueError):
            implicit_curve_polylines(_f2d("x^2 + y^2 = 1"), (1.0, -1.0), RANGE)


class TestImplicitIntersections2D:
    """Giao điểm của hai đường ẩn 2D."""

    def test_circle_and_diagonal_line(self) -> None:
        """Đường tròn r = 5 cắt y = x tại (±5/√2, ±5/√2)."""
        points = find_implicit_intersections(_f2d("x^2 + y^2 = 25"), _f2d("y = x"), RANGE, RANGE)
        expected = 5 / np.sqrt(2)
        assert len(points) == 2
        xs = sorted(p.x for p in points)
        ys = sorted(p.y for p in points)
        assert xs == pytest.approx([-expected, expected], abs=1e-4)
        assert ys == pytest.approx([-expected, expected], abs=1e-4)

    def test_circle_and_parabola(self) -> None:
        """Đường tròn cắt parabol y = x² tại nghiệm của x² + x⁴ = 25."""
        points = find_implicit_intersections(_f2d("x^2 + y^2 = 25"), _f2d("y = x^2"), RANGE, RANGE)
        x_sq = (-1 + np.sqrt(101)) / 2
        expected_x = np.sqrt(x_sq)
        xs = sorted(round(p.x, 4) for p in points)
        assert xs == pytest.approx([-round(expected_x, 4), round(expected_x, 4)], abs=1e-4)
        for p in points:
            assert p.y == pytest.approx(x_sq, abs=1e-4)

    def test_disjoint_circles_have_no_intersection(self) -> None:
        """Hai đường tròn đồng tâm khác bán kính không có điểm chung."""
        assert find_implicit_intersections(_f2d("x^2 + y^2 = 25"), _f2d("x^2 + y^2 = 1"), RANGE, RANGE) == []

    def test_ellipse_crossing_circle(self) -> None:
        """Elip dài hơn bán kính đường tròn thì cắt đường tròn tại bốn điểm đối xứng."""
        points = find_implicit_intersections(
            _f2d("x^2 + y^2 = 9"),
            _f2d("x^2/16 + y^2/4 = 1"),
            RANGE,
            RANGE,
        )
        assert len(points) == 4
        for p in points:
            assert p.x**2 + p.y**2 == pytest.approx(9.0, abs=1e-6)

    def test_identical_curves_return_empty(self) -> None:
        """Hai đường trùng nhau có vô số điểm chung, trả về rỗng để tránh liệt kê hàng nghìn điểm."""
        assert find_implicit_intersections(_f2d("x^2 + y^2 = 4"), _f2d("x^2 + y^2 = 4"), RANGE, RANGE) == []

    def test_every_returned_point_is_on_both_curves(self) -> None:
        """Mọi giao điểm trả về phải thỏa cả hai phương trình."""
        f = _f2d("sin(x) = cos(y)")
        g = _f2d("x^2 + y^2 = 9")
        for p in find_implicit_intersections(f, g, RANGE, RANGE):
            assert abs(f(p.x, p.y)) < 1e-5
            assert abs(g(p.x, p.y)) < 1e-5


class TestImplicitSurface3D:
    """Mặt ẩn 3D và đường giao hai mặt."""

    XS = np.linspace(-6.0, 6.0, 31)

    def test_grid_shape_and_nan_fill(self) -> None:
        """Lưới có hình dạng (nx, ny, nz), NaN được thay bằng số dương lớn để mặt không mở lỗ."""
        values = isosurface_grid(_f3d("sqrt(x) + y + z"), self.XS, self.XS, self.XS)
        assert values.shape == (31, 31, 31)
        assert np.isfinite(values).all()
        # Ô không xác định nhận giá trị của ô lân cận, nên không vượt biên độ của hàm thật (≈ 18 ở đây).
        assert values.max() < 50.0

    def test_plane_meets_sphere_on_circle(self) -> None:
        """Mặt cầu r = 5 cắt mặt phẳng z = 3 theo đường tròn bán kính 4."""
        f = isosurface_grid(_f3d("x^2 + y^2 + z^2 = 25"), self.XS, self.XS, self.XS)
        g = isosurface_grid(_f3d("z = 3"), self.XS, self.XS, self.XS)
        segments = implicit_surface_intersection(f, g, self.XS, self.XS, self.XS)
        assert segments.shape[0] > 0
        points = segments.reshape(-1, 3)
        np.testing.assert_allclose(points[:, 2], 3.0, atol=1e-6)
        radii = np.hypot(points[:, 0], points[:, 1])
        # Đoạn thẳng xấp xỉ đường tròn, nên sai số bán kính tối đa bằng khoảng nửa bước lưới.
        assert np.max(np.abs(radii - 4.0)) < 0.25

    def test_parallel_planes_have_no_intersection(self) -> None:
        """Hai mặt phẳng song song không có đường giao."""
        f = isosurface_grid(_f3d("z = 1"), self.XS, self.XS, self.XS)
        g = isosurface_grid(_f3d("z = 2"), self.XS, self.XS, self.XS)
        assert implicit_surface_intersection(f, g, self.XS, self.XS, self.XS).shape == (0, 2, 3)

    def test_cylinder_meets_cone(self) -> None:
        """Hình trụ x²+y²=9 và hình nón x²+y²=z² cắt nhau tại hai đường tròn z = ±3."""
        f = isosurface_grid(_f3d("x^2 + y^2 = 9"), self.XS, self.XS, self.XS)
        g = isosurface_grid(_f3d("x^2 + y^2 - z^2 = 0"), self.XS, self.XS, self.XS)
        segments = implicit_surface_intersection(f, g, self.XS, self.XS, self.XS)
        points = segments.reshape(-1, 3)
        assert points.size > 0
        assert set(np.round(np.abs(points[:, 2]), 0).tolist()) == {3.0}

    def test_mismatched_grids_raise(self) -> None:
        """Hai lưới khác kích thước bị từ chối."""
        f = np.zeros((4, 4, 4))
        g = np.zeros((4, 4, 5))
        with pytest.raises(ValueError):
            implicit_surface_intersection(f, g, np.arange(4.0), np.arange(4.0), np.arange(4.0))


class TestDomainBoundaryFill:
    """Ô ngoài miền xác định không được tạo mặt ma ở biên."""

    def test_no_artificial_sheet_at_undefined_boundary(self) -> None:
        """sqrt(x) - 1 = z: không có đổi dấu tại x < 0, nơi hàm không xác định."""
        xs = np.linspace(-3.0, 3.0, 31)
        values = isosurface_grid(_f3d("sqrt(x) - 1 = z"), xs, xs, xs)
        assert np.isfinite(values).all()
        negative_x = values[xs < 0]
        flips = (np.sign(negative_x[:-1]) != np.sign(negative_x[1:])).any()
        assert not flips

    def test_fill_keeps_neighbour_sign(self) -> None:
        """Ô NaN nhận dấu của ô lân cận, không bị đảo dấu."""
        from graph_app.implicit import _fill_nearest

        grid = np.array([[[-2.0, np.nan], [-3.0, -4.0]]])
        filled = _fill_nearest(grid)
        assert filled[0, 0, 1] < 0


class TestTangencyAdversarial:
    """Tiếp xúc giữa hai đường ẩn: không đổi dấu nên lưới không thấy, phải có nhánh riêng.

    Mỗi ca có đáp số tính tay. Ca âm tính giả và ca biên giữ cho việc sửa tiếp xúc không tạo điểm ma.
    """

    @staticmethod
    def _points(first: str, second: str, window: float = 10.0, samples: int = 300) -> list[tuple[float, float]]:
        """Giao điểm của hai đường ẩn trong khung ``[-window, window]²``."""
        from graph_app.implicit import find_implicit_intersections

        f = parse_user_equation(first).implicit_2d
        g = parse_user_equation(second).implicit_2d
        return [(p.x, p.y) for p in find_implicit_intersections(f, g, (-window, window), (-window, window), samples)]

    @staticmethod
    def _assert_points(found: list[tuple[float, float]], expected: list[tuple[float, float]], tol: float = 1e-5) -> None:
        """Mỗi điểm kỳ vọng có đúng một điểm tìm được gần, và không có điểm thừa."""
        assert len(found) == len(expected), f"found {found}, expected {expected}"
        for ex, ey in expected:
            assert any(abs(fx - ex) < tol and abs(fy - ey) < tol for fx, fy in found), (ex, ey, found)

    def test_circle_tangent_to_horizontal_line(self) -> None:
        """x² + y² = 25 tiếp xúc y = 5 tại (0, 5)."""
        self._assert_points(self._points("x^2 + y^2 = 25", "y = 5"), [(0.0, 5.0)])

    def test_circle_tangent_to_diagonal_line(self) -> None:
        """x² + y² = 25 tiếp xúc x + y = 5√2 tại (5/√2, 5/√2)."""
        s = 5 / math.sqrt(2.0)
        self._assert_points(self._points("x^2 + y^2 = 25", f"x + y = {5 * math.sqrt(2.0)!r}"), [(s, s)])

    def test_parabola_tangent_to_its_tangent_line(self) -> None:
        """y = x² và tiếp tuyến y = 2x - 1 chạm nhau tại (1, 1)."""
        self._assert_points(self._points("x^2 - y = 0", "2*x - y - 1 = 0"), [(1.0, 1.0)])

    def test_parabola_tangent_off_grid(self) -> None:
        """Tiếp tuyến tại x = 0.3 không nằm trên điểm lưới nào."""
        self._assert_points(self._points("x^2 - y = 0", "0.6*x - y - 0.09 = 0"), [(0.3, 0.09)])

    def test_external_and_internal_tangent_circles(self) -> None:
        """Hai đường tròn tiếp xúc ngoài tại (1, 0). Đường tròn (x-1)² + y² = 1 nằm trong x² + y² = 4 và chạm tại (2, 0); (0, 0) không nằm trên đường tròn r=2."""
        self._assert_points(self._points("x^2 + y^2 = 1", "(x-2)^2 + y^2 = 1"), [(1.0, 0.0)])
        self._assert_points(self._points("x^2 + y^2 = 4", "(x-1)^2 + y^2 = 1"), [(2.0, 0.0)])

    def test_cosine_touches_line_at_several_points(self) -> None:
        """y = cos(x) chạm y = 1 tại x = 0, ±2π trên [-10, 10]: nhiều tiếp điểm trong một cặp."""
        self._assert_points(
            self._points("y - cos(x) = 0", "y = 1"),
            [(0.0, 1.0), (2 * math.pi, 1.0), (-2 * math.pi, 1.0)],
        )

    def test_node_and_cusp_through_origin(self) -> None:
        """Nút x² - y² = 0 và cusp y² = x³ cùng đi qua gốc và cắt y = 0 tại đó."""
        self._assert_points(self._points("x^2 - y^2 = 0", "y = 0"), [(0.0, 0.0)])
        self._assert_points(self._points("y^2 - x^3 = 0", "y = 0"), [(0.0, 0.0)])

    def test_tangent_node_exactly_on_grid(self) -> None:
        """Lưới lẻ 301 có điểm x = 0 chính xác; tiếp điểm trùng điểm lưới không được mất hay nhân đôi."""
        self._assert_points(self._points("x^2 + y^2 = 25", "y = 5", samples=301), [(0.0, 5.0)])

    def test_nearly_tangent_but_crossing_gives_two_points(self) -> None:
        """y = 4.999 cắt đường tròn r = 5 tại hai điểm x = ±√(25 - 4.999²), không được gộp thành một."""
        half = math.sqrt(25 - 4.999**2)
        self._assert_points(self._points("x^2 + y^2 = 25", "y = 4.999"), [(-half, 4.999), (half, 4.999)])

    def test_no_false_positive_for_a_gap(self) -> None:
        """y = 5.001 không chạm đường tròn r = 5. Khoảng cách 0.001 phải cho không có điểm nào."""
        assert self._points("x^2 + y^2 = 25", "y = 5.001") == []

    def test_identical_curves_list_nothing(self) -> None:
        """Hai đường trùng nhau có vô số điểm chung, hàm trả về rỗng."""
        assert self._points("x^2 + y^2 = 25", "x^2 + y^2 = 25") == []

    def test_tangent_coordinates_are_snapped_to_zero(self) -> None:
        """Tiếp điểm tại x = 0 không trả về -2e-9; phải là 0.0 chính xác để nhãn không hiện "-0.0000"."""
        ((x, y),) = self._points("x^2 + y^2 = 25", "y = 5")
        assert x == 0.0
