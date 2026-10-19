"""Unit test cho ``graph_app.plotting``: khung tung độ, cắt gián đoạn và dựng biểu đồ."""

from __future__ import annotations

import numpy as np
import pytest

from graph_app.math_engine import Intersection, parse_expression, sample_function
from graph_app.plotting import (
    DEFAULT_Y_RANGE,
    PALETTE,
    PLOT_SIZE_PX,
    _LABEL_CANDIDATES,
    Curve,
    IntersectionMarker,
    _label_box_size,
    _overlap_area,
    break_discontinuities,
    build_figure,
    compute_y_range,
    place_labels,
)


def _curve(text: str, x_min: float = -5.0, x_max: float = 5.0, index: int = 0) -> Curve:
    """Tạo một ``Curve`` từ biểu thức để dùng trong test."""
    func = parse_expression(text)
    x, y = sample_function(func, x_min, x_max, 500)
    return Curve(label=text, color=PALETTE[index], x=x, y=y)


class TestComputeYRange:
    """Kiểm tra cách xác định khung tung độ."""

    def test_empty_input_uses_default_range(self) -> None:
        """Không có dữ liệu hữu hạn thì dùng khung mặc định."""
        assert compute_y_range([], []) == pytest.approx(DEFAULT_Y_RANGE)

    def test_range_contains_all_finite_values(self) -> None:
        """Khung tung độ bao phủ các giá trị hữu hạn của đường cong."""
        curve = _curve("x")
        low, high = compute_y_range([curve], [])
        assert low < -5.0
        assert high > 5.0

    def test_asymptote_does_not_dominate_range(self) -> None:
        """Giá trị tiệm cận cực lớn của tan(x) không làm khung nở ra vô hạn."""
        curve = _curve("tan(x)", -3.0, 3.0)
        low, high = compute_y_range([curve], [])
        assert abs(low) < 1e4
        assert abs(high) < 1e4

    def test_range_includes_intersection_points(self) -> None:
        """Khung luôn bao gồm tung độ của mọi giao điểm."""
        curve = _curve("x", -1.0, 1.0)
        marker = IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=0.0, y=50.0))
        _, high = compute_y_range([curve], [marker])
        assert high > 50.0

    def test_constant_curve_gets_nonzero_height(self) -> None:
        """Hàm hằng vẫn có khung có chiều cao dương để trục không bị suy biến."""
        curve = _curve("3")
        low, high = compute_y_range([curve], [])
        assert high > low


class TestBreakDiscontinuities:
    """Kiểm tra việc cắt đường vẽ tại điểm gián đoạn."""

    def test_large_jump_is_cut(self) -> None:
        """Bước nhảy lớn hơn ngưỡng bị thay bằng NaN, không nối qua tiệm cận."""
        y = np.array([0.0, 1.0, 1000.0, 1001.0])
        cleaned = break_discontinuities(y, frame_height=10.0)
        assert np.isnan(cleaned[2])
        assert cleaned[3] == pytest.approx(1001.0)

    def test_smooth_curve_is_unchanged(self) -> None:
        """Đường trơn không có bước nhảy thì giữ nguyên toàn bộ giá trị."""
        y = np.linspace(0.0, 1.0, 50)
        cleaned = break_discontinuities(y, frame_height=10.0)
        np.testing.assert_allclose(cleaned, y)

    def test_input_is_not_mutated(self) -> None:
        """Hàm không sửa mảng đầu vào, chỉ trả về bản sao."""
        y = np.array([0.0, 1000.0])
        break_discontinuities(y, frame_height=1.0)
        assert y[1] == 1000.0


class TestBuildFigure:
    """Kiểm tra cấu trúc biểu đồ Plotly."""

    def test_one_trace_per_curve_plus_markers(self) -> None:
        """Mỗi đường cong là một trace, cộng một trace cho các điểm giao."""
        curves = [_curve("x", index=0), _curve("x^2", index=1)]
        markers = [IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=0.0, y=0.0))]
        fig = build_figure(curves, markers, (-5.0, 5.0))
        assert len(fig.data) == 3
        assert fig.data[-1].mode == "markers"

    def test_each_intersection_has_annotation_with_coordinates(self) -> None:
        """Mỗi giao điểm có một chú thích ghi tọa độ (x; y)."""
        markers = [
            IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=1.5, y=-2.25)),
            IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=-1.5, y=2.25)),
        ]
        fig = build_figure([_curve("x")], markers, (-5.0, 5.0))
        texts = [a.text for a in fig.layout.annotations]
        assert len(texts) == 2
        assert "(1.5000; -2.2500)" in texts[0]
        assert "(-1.5000; 2.2500)" in texts[1]

    def test_no_intersections_means_no_marker_trace(self) -> None:
        """Không có giao điểm thì không thêm trace điểm và không có chú thích."""
        fig = build_figure([_curve("x")], [], (-5.0, 5.0))
        assert len(fig.data) == 1
        assert len(fig.layout.annotations) == 0

    def test_dark_theme_is_applied(self) -> None:
        """Biểu đồ dùng template tối và nền trong suốt để hòa vào giao diện Dark Mode."""
        fig = build_figure([_curve("x")], [], (-5.0, 5.0))
        assert fig.layout.template.layout.paper_bgcolor is not None
        assert fig.layout.paper_bgcolor == "rgba(0, 0, 0, 0)"

    def test_axis_range_matches_request(self) -> None:
        """Trục x hiển thị đúng khoảng người dùng chọn."""
        fig = build_figure([_curve("x")], [], (-7.0, 9.0))
        assert list(fig.layout.xaxis.range) == [-7.0, 9.0]

    def test_curves_use_distinct_colors(self) -> None:
        """Mỗi đường cong có màu riêng, không trùng nhau."""
        curves = [_curve("x", index=i) for i in range(3)]
        fig = build_figure(curves, [], (-5.0, 5.0))
        colors = [trace.line.color for trace in fig.data]
        assert len(set(colors)) == 3

    def test_palette_has_six_distinct_colors(self) -> None:
        """Bảng màu có đủ sáu màu khác nhau cho tối đa sáu hàm số."""
        assert len(PALETTE) == 6
        assert len(set(PALETTE)) == 6


class TestLabelPlacement:
    """Chống chồng chữ: chú thích giao điểm không được đè lên nhau khi các điểm gần nhau."""

    @staticmethod
    def _boxes(markers: list[IntersectionMarker], offsets: list[tuple[int, int] | None],
               x_range: tuple[float, float], y_range: tuple[float, float]) -> list[tuple[float, float, float, float]]:
        """Tính hình chữ nhật pixel của từng chú thích đang hiện. Nhãn bị ẩn (``None``) bị bỏ qua."""
        width, height = PLOT_SIZE_PX
        boxes = []
        for marker, offset in zip(markers, offsets, strict=True):
            if offset is None:
                continue
            ax, ay = offset
            px = (marker.point.x - x_range[0]) / (x_range[1] - x_range[0]) * width
            py = (y_range[1] - marker.point.y) / (y_range[1] - y_range[0]) * height
            w, h = _label_box_size(marker)
            cx, cy = px + ax, py + ay
            boxes.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        return boxes

    def test_close_points_get_non_overlapping_labels(self) -> None:
        """Bốn giao điểm nằm rất sát nhau vẫn có chú thích không chồng lên nhau."""
        markers = [
            IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=0.0 + 0.01 * i, y=0.0 + 0.01 * i))
            for i in range(4)
        ]
        x_range, y_range = (-10.0, 10.0), (-10.0, 10.0)
        offsets = place_labels(markers, x_range, y_range)
        assert all(offset is not None for offset in offsets)
        boxes = self._boxes(markers, offsets, x_range, y_range)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                assert _overlap_area(boxes[i], boxes[j]) == 0.0

    def test_single_point_uses_first_candidate(self) -> None:
        """Một giao điểm đơn lẻ dùng vị trí ưu tiên đầu tiên."""
        markers = [IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=1.0, y=1.0))]
        offsets = place_labels(markers, (-10.0, 10.0), (-10.0, 10.0))
        assert offsets == [_LABEL_CANDIDATES[0]]

    def test_offsets_count_matches_markers(self) -> None:
        """Mỗi giao điểm nhận đúng một độ lệch."""
        markers = [IntersectionMarker(pair="p", point=Intersection(x=float(i), y=0.0)) for i in range(7)]
        assert len(place_labels(markers, (-10.0, 10.0), (-10.0, 10.0))) == 7

    def test_crowded_points_hide_labels_instead_of_overlapping(self) -> None:
        """Nhiều điểm nằm trên một hàng quá dày: một số nhãn bị ẩn, nhãn còn lại không chồng nhau."""
        markers = [IntersectionMarker(pair="f1 ∩ f2", point=Intersection(x=0.3 * i, y=0.0)) for i in range(30)]
        x_range, y_range = (-10.0, 10.0), (-10.0, 10.0)
        offsets = place_labels(markers, x_range, y_range)
        assert any(offset is None for offset in offsets)
        boxes = self._boxes(markers, offsets, x_range, y_range)
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                assert _overlap_area(boxes[i], boxes[j]) == 0.0


class TestImplicitCurveRendering:
    """Đường ẩn được vẽ liền mạch, không bị cắt như hàm y = f(x)."""

    def test_implicit_curve_is_not_cut(self) -> None:
        """Đường đứng có bước nhảy lớn theo y vẫn không bị cắt khi ``cut_jumps=False``."""
        y = np.array([-10.0, -5.0, 5.0, 10.0])
        curve = Curve(label="ẩn", color=PALETTE[0], x=np.zeros(4), y=y, cut_jumps=False)
        fig = build_figure([curve], [], (-1.0, 1.0), y_range=(-10.0, 10.0))
        np.testing.assert_allclose(fig.data[0].y, y)

    def test_explicit_curve_is_still_cut_at_asymptote(self) -> None:
        """Hàm ``y = f(x)`` vẫn cắt tại tiệm cận, giữ hành vi cũ."""
        y = np.array([0.0, 1000.0])
        curve = Curve(label="f", color=PALETTE[0], x=np.array([0.0, 1.0]), y=y, cut_jumps=True)
        fig = build_figure([curve], [], (-1.0, 2.0), y_range=(-10.0, 10.0))
        assert np.isnan(fig.data[0].y[1])

    def test_fixed_y_range_is_applied(self) -> None:
        """Khi người dùng tắt khung tự động, trục y dùng đúng khoảng đã chọn."""
        curve = _curve("x")
        fig = build_figure([curve], [], (-5.0, 5.0), y_range=(-7.0, 9.0))
        assert list(fig.layout.yaxis.range) == [-7.0, 9.0]


class TestAsymptoteRule:
    """Tiệm cận được cắt ngay cả khi khung chung rất cao; nghiệm thật không bị cắt nhầm."""

    def test_asymptote_cut_even_with_huge_shared_frame(self) -> None:
        """tan(x) vẽ cùng x^5: tiệm cận ±π/2 vẫn bị cắt, không còn đường ma nối qua."""
        from graph_app.plotting import Curve

        xs, tan_y = sample_function(parse_expression("tan(x)"), -6.0, 6.0, 1500)
        _, big_y = sample_function(parse_expression("x^5"), -6.0, 6.0, 1500)
        frame = compute_y_range(
            [Curve("t", "#fff", xs, tan_y), Curve("b", "#fff", xs, big_y)],
            [],
        )
        cleaned = break_discontinuities(tan_y, frame[1] - frame[0])
        crossing = np.isfinite(cleaned[:-1]) & np.isfinite(cleaned[1:]) & (np.sign(cleaned[:-1]) != np.sign(cleaned[1:]))
        # Các điểm đổi dấu còn lại phải là nghiệm thật của tan(x) tại 0 và ±π, không phải tiệm cận.
        crossing_x = xs[:-1][crossing]
        assert all(min(abs(crossing_x - root)) < 0.02 for root in (0.0, np.pi, -np.pi))

    def test_smooth_zero_crossing_is_kept(self) -> None:
        """Hàm x đi qua 0 là nghiệm thật, không được cắt."""
        xs, y = sample_function(parse_expression("x"), -6.0, 6.0, 1500)
        assert np.isnan(break_discontinuities(y, 100.0)).sum() == 0


class TestAxes2D:
    """Cả hai trục 2D đều được vẽ rõ, có tên trục và nhãn."""

    def test_both_axes_are_visible_with_titles(self) -> None:
        """Trục x và y đều hiện đường trục, nhãn số và tên trục."""
        fig = build_figure([_curve("x")], [], (-5.0, 5.0), (-5.0, 5.0))
        for axis, name in ((fig.layout.xaxis, "x"), (fig.layout.yaxis, "y")):
            assert axis.showline is True
            assert axis.showticklabels is True
            assert axis.title.text == name

    def test_zero_lines_use_visible_color(self) -> None:
        """Đường trục tại 0 dùng màu đủ sáng, không bị chìm vào nền tối."""
        from graph_app.plotting import AXIS_LINE_COLOR

        fig = build_figure([_curve("x")], [], (-5.0, 5.0), (-5.0, 5.0))
        assert fig.layout.yaxis.zerolinecolor == AXIS_LINE_COLOR
        assert fig.layout.xaxis.zerolinecolor == AXIS_LINE_COLOR
