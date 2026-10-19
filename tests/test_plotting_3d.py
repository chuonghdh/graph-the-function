"""Unit test cho ``graph_app.plotting_3d``: khung z, bảng màu và cấu trúc biểu đồ 3D."""

from __future__ import annotations

import numpy as np
import pytest
from plotly.colors import get_colorscale

from graph_app.math_engine import parse_expression
from graph_app.plotting_3d import (
    COLORSCALES,
    DEFAULT_Z_RANGE,
    PairCurve,
    build_figure_3d,
    compute_z_range,
)
from graph_app.surface import SpacePolyline, Surface, evaluate_surface, intersection_curves, make_grid

XY = ("x", "y")


def _colors(scale: object) -> list[str]:
    """Lấy danh sách mã màu từ một bảng màu Plotly, bỏ qua vị trí."""
    return [str(stop[1]) for stop in scale]  # type: ignore[attr-defined]


def _surface(text: str, resolution: int = 15) -> Surface:
    """Tạo một mặt trên lưới đều quanh gốc tọa độ."""
    xs, ys = make_grid((-2.0, 2.0), (-2.0, 2.0), resolution)
    return Surface(label=text, xs=xs, ys=ys, zs=evaluate_surface(parse_expression(text, variables=XY), xs, ys))


class TestComputeZRange:
    """Kiểm tra cách xác định khung z."""

    def test_empty_input_uses_default(self) -> None:
        """Không có dữ liệu thì dùng khung mặc định, không thêm phần đệm."""
        assert compute_z_range([], []) == DEFAULT_Z_RANGE

    def test_range_covers_surface_values(self) -> None:
        """Khung z bao phủ các giá trị hữu hạn của mặt."""
        low, high = compute_z_range([_surface("x + y")], [])
        assert low < -4.0
        assert high > 4.0

    def test_spike_does_not_dominate_range(self) -> None:
        """Đỉnh nhọn cực lớn như 1/(x²+y²) gần gốc không làm khung nở ra vô hạn."""
        spike = _surface("1/(x^2 + y^2 + 0.0001)", resolution=101)
        low, high = compute_z_range([spike], [])
        assert high < 1e4

    def test_flat_surface_gets_nonzero_height(self) -> None:
        """Mặt phẳng nằm ngang vẫn có khung có chiều cao dương."""
        low, high = compute_z_range([_surface("3")], [])
        assert high > low


class TestBuildFigure3D:
    """Kiểm tra cấu trúc biểu đồ 3D Plotly."""

    def test_one_surface_trace_per_surface(self) -> None:
        """Mỗi mặt là một trace Surface, không gộp hay bỏ sót."""
        surfaces = [_surface("x^2 + y^2"), _surface("x + y")]
        fig = build_figure_3d(surfaces, [], ["Viridis", "Plasma"], (-2, 2), (-2, 2))
        assert [t.type for t in fig.data] == ["surface", "surface"]

    def test_colorscales_are_applied_per_surface(self) -> None:
        """Mỗi mặt nhận đúng bảng màu đã chọn."""
        surfaces = [_surface("x^2 + y^2"), _surface("x + y")]
        fig = build_figure_3d(surfaces, [], ["Turbo", "Electric"], (-2, 2), (-2, 2))
        # Plotly mở tên bảng màu thành danh sách (vị trí, mã màu), nên so với danh sách gốc.
        assert _colors(fig.data[0].colorscale) == _colors(get_colorscale("Turbo"))
        assert _colors(fig.data[1].colorscale) == _colors(get_colorscale("Electric"))

    def test_curve_is_drawn_as_scatter3d_line(self) -> None:
        """Đường giao được vẽ như Scatter3d kiểu đường, không phải mặt."""
        surfaces = [_surface("x^2 + y^2")]
        curve = SpacePolyline(points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]]))
        fig = build_figure_3d(surfaces, [curve], ["Viridis"], (-2, 2), (-2, 2))
        assert fig.data[-1].type == "scatter3d"
        assert fig.data[-1].mode == "lines+markers"
        # Đường không có điểm cô lập: marker có kích thước 0, nên không hiện chấm nào.
        assert set(np.asarray(fig.data[-1].marker.size).tolist()) == {0}

    def test_scene_axes_follow_requested_ranges(self) -> None:
        """Ba trục nhận đúng khoảng x, y và khung z đã tính."""
        fig = build_figure_3d([_surface("x")], [], ["Viridis"], (-1.0, 3.0), (-2.0, 5.0))
        assert list(fig.layout.scene.xaxis.range) == [-1.0, 3.0]
        assert list(fig.layout.scene.yaxis.range) == [-2.0, 5.0]
        assert fig.layout.scene.zaxis.range is not None

    def test_dark_scene_background(self) -> None:
        """Nền biểu đồ trong suốt để hòa vào giao diện Dark Mode."""
        fig = build_figure_3d([_surface("x")], [], ["Viridis"], (-2, 2), (-2, 2))
        assert fig.layout.paper_bgcolor == "rgba(0, 0, 0, 0)"
        assert fig.layout.template.layout.paper_bgcolor is not None

    def test_mismatched_colorscale_count_raises(self) -> None:
        """Số bảng màu phải khớp số mặt."""
        with pytest.raises(ValueError):
            build_figure_3d([_surface("x")], [], [], (-2, 2), (-2, 2))

    def test_all_offered_colorscales_are_valid_plotly_names(self) -> None:
        """Mọi bảng màu được liệt kê trong UI phải là tên hợp lệ của Plotly."""
        surfaces = [_surface("x")]
        for name in COLORSCALES:
            fig = build_figure_3d(surfaces, [], [name], (-2, 2), (-2, 2))
            assert fig.data[0].colorscale is not None

    def test_real_intersection_curve_renders(self) -> None:
        """Đường giao thật từ hai mặt đưa vào biểu đồ được mà không lỗi."""
        xs, ys = make_grid((-3.0, 3.0), (-3.0, 3.0), 81)
        func = parse_expression("sin(sqrt(x^2 + y^2))", variables=XY)
        a = Surface("a", xs, ys, evaluate_surface(func, xs, ys))
        b = Surface("b", xs, ys, evaluate_surface(parse_expression("0.3*x + 0.1*y", variables=XY), xs, ys))
        curves = intersection_curves(a, b, func)
        fig = build_figure_3d([a, b], curves, ["Viridis", "Plasma"], (-3, 3), (-3, 3))
        # Mọi đường giao được gộp vào một trace Scatter3d, nên chỉ thêm đúng một trace.
        assert len(fig.data) == 2 + 1


class TestBuildSceneMixed:
    """Cảnh chung: mặt tường minh, mặt ẩn và đường giao trong cùng một biểu đồ."""

    def test_surface_isosurface_and_curves_coexist(self) -> None:
        """Một mặt tường minh, một mặt ẩn và đường giao đều có trace riêng trong cùng cảnh."""
        from graph_app.implicit import isosurface_grid
        from graph_app.plotting_3d import ImplicitSurface, build_scene_3d

        xs, ys = make_grid((-2.0, 2.0), (-2.0, 2.0), 15)
        zs = np.linspace(-2.0, 2.0, 15)
        surface = _surface("x + y")
        sphere = parse_expression("x^2 + y^2 + z^2 - 1", variables=("x", "y", "z"))
        iso = ImplicitSurface(
            label="sphere",
            colorscale="Turbo",
            xs=xs,
            ys=ys,
            zs=zs,
            values=isosurface_grid(sphere, xs, ys, zs),
        )
        curve = SpacePolyline(points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]))
        fig = build_scene_3d(
            surfaces=[surface],
            surface_colorscales=["Viridis"],
            isosurfaces=[iso],
            pair_curves=[PairCurve(label="f1 ∩ f2", color="#FF9F1C", points=curve.points)],
            x_range=(-2, 2),
            y_range=(-2, 2),
            z_range=(-2, 2),
        )
        assert [t.type for t in fig.data] == ["surface", "isosurface", "scatter3d"]
        assert fig.data[-1].name == "f1 ∩ f2"
        assert fig.data[-1].line.color == "#FF9F1C"

    def test_isosurface_uses_zero_level_only(self) -> None:
        """Mặt ẩn chỉ vẽ mức 0, không vẽ nhiều mức."""
        from graph_app.implicit import isosurface_grid
        from graph_app.plotting_3d import ImplicitSurface, build_scene_3d

        xs = np.linspace(-1.0, 1.0, 9)
        values = isosurface_grid(parse_expression("x + y + z", variables=("x", "y", "z")), xs, xs, xs)
        iso = ImplicitSurface("plane", "Viridis", xs, xs, xs, values)
        fig = build_scene_3d([], [], [iso], [], (-1, 1), (-1, 1), (-1, 1))
        assert fig.data[0].isomin == 0.0
        assert fig.data[0].isomax == 0.0
        assert fig.data[0].surface.count == 1

    def test_mismatched_colorscale_count_raises(self) -> None:
        """Số bảng màu tường minh phải khớp số mặt."""
        from graph_app.plotting_3d import build_scene_3d

        with pytest.raises(ValueError):
            build_scene_3d([_surface("x")], [], [], [], (-1, 1), (-1, 1), (-1, 1))


class TestColorbarLabels:
    """Thanh màu của nhiều mặt không được chồng lên nhau, và tiêu đề chỉ là tên ngắn."""

    def test_colorbar_titles_are_short_names(self) -> None:
        """Tiêu đề thanh màu là f1, f2, không phải toàn bộ biểu thức."""
        surfaces = [_surface("x^2 + y^2"), _surface("x + y")]
        surfaces[0] = Surface(label="f1: z = x^2 + y^2", xs=surfaces[0].xs, ys=surfaces[0].ys, zs=surfaces[0].zs)
        surfaces[1] = Surface(label="f2: z = x + y", xs=surfaces[1].xs, ys=surfaces[1].ys, zs=surfaces[1].zs)
        fig = build_figure_3d(surfaces, [], ["Viridis", "Plasma"], (-2, 2), (-2, 2))
        assert [t.colorbar.title.text for t in fig.data] == ["f1", "f2"]

    def test_colorbars_are_placed_at_different_x(self) -> None:
        """Mỗi thanh màu có vị trí ngang riêng, không đè lên thanh khác."""
        surfaces = [_surface("x^2 + y^2"), _surface("x + y"), _surface("x - y")]
        fig = build_figure_3d(surfaces, [], ["Viridis", "Plasma", "Turbo"], (-2, 2), (-2, 2))
        positions = [t.colorbar.x for t in fig.data]
        assert len(set(positions)) == 3
