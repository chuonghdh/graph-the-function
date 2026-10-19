"""Kiểm tra màu theo cặp giao, chế độ làm nổi bật (Focus Mode) và văn bản giao tuyến."""

from __future__ import annotations

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from graph_app.math_engine import Intersection
from graph_app.plotting import DIM_OPACITY, PAIR_COLORS, Curve, IntersectionMarker, build_figure, pair_color
from graph_app.plotting_3d import PairCurve, build_scene_3d
from graph_app.ui_focus import system_text


def _curve(index: int) -> Curve:
    """Một đường cong đơn giản để dựng biểu đồ."""
    x = np.linspace(-1.0, 1.0, 5)
    return Curve(label=f"f{index}", color="#00F0FF", x=x, y=x)


def _marker(pair: str, x: float, y: float) -> IntersectionMarker:
    """Một giao điểm thuộc cặp cho trước."""
    return IntersectionMarker(pair=pair, point=Intersection(x=x, y=y))


class TestPairColors:
    """Mỗi cặp có màu riêng, và chú thích dùng đúng màu đó."""

    def test_pair_colors_are_distinct(self) -> None:
        """Mọi cặp của tối đa sáu hàm (15 cặp) có màu khác nhau."""
        assert len(PAIR_COLORS) == 15
        assert len(set(PAIR_COLORS.values())) == 15

    def test_unknown_pair_falls_back_to_white(self) -> None:
        """Cặp chưa khai báo nhận màu dự phòng, không gây lỗi."""
        assert pair_color("f9 ∩ f8") == "#FFFFFF"

    def test_annotation_font_matches_marker_color(self) -> None:
        """Màu chữ chú thích trùng màu của cặp giao."""
        markers = [_marker("f1 ∩ f3", 0.0, 0.0)]
        fig = build_figure([_curve(1)], markers, (-1.0, 1.0), (-1.0, 1.0))
        assert fig.layout.annotations[0].font.color == PAIR_COLORS["f1 ∩ f3"]

    def test_marker_trace_color_matches_pair(self) -> None:
        """Điểm giao của một cặp được vẽ bằng màu của cặp đó."""
        markers = [_marker("f2 ∩ f3", 0.0, 0.0)]
        fig = build_figure([_curve(1)], markers, (-1.0, 1.0), (-1.0, 1.0))
        marker_trace = fig.data[-1]
        assert marker_trace.name == "f2 ∩ f3"
        assert marker_trace.marker.color == PAIR_COLORS["f2 ∩ f3"]


class TestFocusMode2D:
    """Khi làm nổi bật, phần không được chọn bị làm mờ."""

    def test_no_focus_keeps_everything_opaque(self) -> None:
        """Không làm nổi bật thì đường cong và điểm giao đều rõ."""
        markers = [_marker("f1 ∩ f2", 0.0, 0.0)]
        fig = build_figure([_curve(1)], markers, (-1.0, 1.0), (-1.0, 1.0), focus_pairs=None)
        assert fig.data[0].opacity == 1.0
        assert fig.data[-1].opacity == 1.0

    def test_focus_dims_curves_and_other_pairs(self) -> None:
        """Chọn một cặp: đường cong mờ, cặp khác mờ, cặp được chọn rõ và lớn hơn."""
        markers = [_marker("f1 ∩ f2", 0.0, 0.0), _marker("f2 ∩ f3", 0.5, 0.5)]
        fig = build_figure(
            [_curve(1)],
            markers,
            (-1.0, 1.0),
            (-1.0, 1.0),
            focus_pairs=frozenset({"f1 ∩ f2"}),
        )
        assert fig.data[0].opacity == pytest.approx(DIM_OPACITY)
        by_name = {t.name: t for t in fig.data}
        assert by_name["f1 ∩ f2"].opacity == 1.0
        assert by_name["f1 ∩ f2"].marker.size > by_name["f2 ∩ f3"].marker.size
        assert by_name["f2 ∩ f3"].opacity < 1.0

    def test_dimmed_annotations_are_transparent(self) -> None:
        """Chú thích của cặp không được chọn trong suốt, để không che phần nổi bật."""
        markers = [_marker("f1 ∩ f2", 0.0, 0.0), _marker("f2 ∩ f3", 0.5, 0.5)]
        fig = build_figure(
            [_curve(1)],
            markers,
            (-1.0, 1.0),
            (-1.0, 1.0),
            focus_pairs=frozenset({"f1 ∩ f2"}),
        )
        opacities = {a.text.split("<br>")[0]: a.opacity for a in fig.layout.annotations}
        assert opacities["<b>f1 ∩ f2</b>"] == 1.0
        assert opacities["<b>f2 ∩ f3</b>"] < 1.0


class TestFocusMode3D:
    """Trong cảnh 3D, mặt gốc được làm mờ và đường giao được chọn phóng to."""

    @staticmethod
    def _points() -> np.ndarray:
        """Một đoạn đường giao ba chiều."""
        return np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])

    def test_focus_dims_surfaces_and_widens_selected_curve(self) -> None:
        """Mặt gốc mờ đi, đường được chọn dày hơn đường còn lại."""
        from graph_app.surface import Surface

        xs = np.linspace(-1.0, 1.0, 4)
        surface = Surface(label="s", xs=xs, ys=xs, zs=np.zeros((4, 4)))
        curves = [
            PairCurve(label="f1 ∩ f2", color=PAIR_COLORS["f1 ∩ f2"], points=self._points()),
            PairCurve(label="f2 ∩ f3", color=PAIR_COLORS["f2 ∩ f3"], points=self._points()),
        ]
        fig = build_scene_3d(
            [surface], ["Viridis"], [], curves, (-1, 1), (-1, 1), (-1, 1),
            focus_pairs=frozenset({"f1 ∩ f2"}),
        )
        assert fig.data[0].opacity < 0.5
        by_name = {t.name: t for t in fig.data if t.type == "scatter3d"}
        assert by_name["f1 ∩ f2"].line.width > by_name["f2 ∩ f3"].line.width
        assert by_name["f2 ∩ f3"].opacity < 1.0

    def test_no_focus_keeps_surfaces_opaque(self) -> None:
        """Không làm nổi bật thì mặt và đường đều rõ."""
        from graph_app.surface import Surface

        xs = np.linspace(-1.0, 1.0, 4)
        surface = Surface(label="s", xs=xs, ys=xs, zs=np.zeros((4, 4)))
        curves = [PairCurve(label="f1 ∩ f2", color=PAIR_COLORS["f1 ∩ f2"], points=self._points())]
        fig = build_scene_3d([surface], ["Viridis"], [], curves, (-1, 1), (-1, 1), (-1, 1))
        assert fig.data[0].opacity > 0.8
        assert fig.data[-1].opacity == 1.0


class TestSystemText:
    """Văn bản giao tuyến theo chuẩn toán học, không có cụm từ về tô sáng."""

    def test_text_names_both_equations(self) -> None:
        """Câu mô tả chứa đủ hai phương trình gốc."""
        text = system_text("x^2 + y^2 + z^2 = 16", "z = x + y")
        assert "x^2 + y^2 + z^2 = 16" in text
        assert "z = x + y" in text

    def test_text_never_mentions_highlighting(self) -> None:
        """Không được viết cụm 'được tô sáng' trong thông báo."""
        assert "tô sáng" not in system_text("x = 1", "y = 2").lower()


class TestHighlightCheckboxes:
    """Checkbox dưới đồ thị: mặc định không tích, tích thì làm nổi bật đúng cặp."""

    @staticmethod
    def _app() -> AppTest:
        """Khởi tạo ứng dụng với mặc định hai hàm, có giao điểm."""
        from pathlib import Path

        app = str(Path(__file__).resolve().parents[1] / "app.py")
        return AppTest.from_file(app, default_timeout=60).run()

    def test_checkboxes_are_unchecked_by_default(self) -> None:
        """Mọi checkbox làm nổi bật đều không tích khi mở ứng dụng."""
        at = self._app()
        boxes = [c for c in at.checkbox if c.key.startswith("highlight::")]
        assert boxes, "phải có checkbox cho mỗi cặp có kết quả"
        assert all(c.value is False for c in boxes)

    def test_checking_a_pair_renders_without_error(self) -> None:
        """Tích checkbox của một cặp: không lỗi, và chỉ cặp đó được giữ nguyên độ mờ."""
        at = self._app()
        at.checkbox(key="highlight::f1 ∩ f2").check().run()
        assert not at.exception
        assert at.checkbox(key="highlight::f1 ∩ f2").value is True

    def test_unchecking_restores_default(self) -> None:
        """Bỏ tích trả về trạng thái mặc định, không lỗi."""
        at = self._app()
        at.checkbox(key="highlight::f1 ∩ f2").check().run()
        at.checkbox(key="highlight::f1 ∩ f2").uncheck().run()
        assert not at.exception
        assert at.checkbox(key="highlight::f1 ∩ f2").value is False

    def test_pair_without_result_has_disabled_checkbox(self) -> None:
        """Cặp không có giao điểm có checkbox bị vô hiệu hóa."""
        at = self._app()
        # Hai đường song song y = x và y = x + 100 không bao giờ cắt nhau.
        at.text_input(key="eq_0").input("x").run()
        at.text_input(key="eq_1").input("x + 100").run()
        assert not at.exception
        box = at.checkbox(key="highlight::f1 ∩ f2")
        assert box.disabled is True


class TestCleanup:
    """Giao diện tối giản: không legend cho giao điểm/giao tuyến, không văn bản đếm đoạn."""

    def test_pair_markers_have_no_legend_entry(self) -> None:
        """Điểm giao không hiện trong chú thích của Plotly."""
        markers = [_marker("f1 ∩ f2", 0.0, 0.0)]
        fig = build_figure([_curve(1)], markers, (-1.0, 1.0), (-1.0, 1.0))
        assert fig.data[-1].showlegend is False

    def test_pair_curves_have_no_legend_entry_in_3d(self) -> None:
        """Đường giao 3D không hiện trong chú thích, và cảnh tắt legend hoàn toàn."""
        from graph_app.surface import Surface

        xs = np.linspace(-1.0, 1.0, 4)
        surface = Surface(label="s", xs=xs, ys=xs, zs=np.zeros((4, 4)))
        curves = [PairCurve(label="f1 ∩ f2", color=PAIR_COLORS["f1 ∩ f2"], points=np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]))]
        fig = build_scene_3d([surface], ["Viridis"], [], curves, (-1, 1), (-1, 1), (-1, 1))
        assert fig.data[-1].showlegend is False
        assert fig.layout.showlegend is False

    def test_row_text_has_no_segment_count(self) -> None:
        """Dòng giao tuyến không còn cụm đếm số đoạn."""
        assert "đoạn" not in system_text("x = 1", "y = 2")


class TestLegendBar:
    """Thanh legend phía trên biểu đồ: mặc định tích hết, bỏ tích thì làm mờ hàm và cặp liên quan."""

    @staticmethod
    def _app() -> AppTest:
        """Ứng dụng với mặc định hai hàm 2D."""
        from pathlib import Path

        app = str(Path(__file__).resolve().parents[1] / "app.py")
        return AppTest.from_file(app, default_timeout=60).run()

    def test_legend_checkboxes_are_ticked_by_default(self) -> None:
        """Mọi checkbox legend đều được tích khi mở ứng dụng."""
        at = self._app()
        boxes = [c for c in at.checkbox if c.key.startswith("legend_") and not c.key.startswith("legend_box")]
        assert len(boxes) == 2
        assert all(c.value is True for c in boxes)

    def test_unticking_dims_the_function_and_its_pairs(self) -> None:
        """Bỏ tích f1: đường f1 và cặp f1 ∩ f2 mờ, còn f2 giữ nguyên độ đậm."""
        import json

        at = self._app()
        at.checkbox(key="legend_0").uncheck().run()
        assert not at.exception
        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        opacity = {t["name"]: t.get("opacity", 1.0) for t in spec["data"]}
        assert opacity["f1(x) = x^2 - 2"] == pytest.approx(0.15)
        assert opacity["f2(x) = sin(x)"] == pytest.approx(1.0)
        assert opacity["f1 ∩ f2"] < 1.0

    def test_reticking_restores_full_opacity(self) -> None:
        """Tích lại thì độ đậm trở về bình thường."""
        import json

        at = self._app()
        at.checkbox(key="legend_0").uncheck().run()
        at.checkbox(key="legend_0").check().run()
        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        assert all(t.get("opacity", 1.0) == pytest.approx(1.0) for t in spec["data"])


class TestNameHelpers:
    """Tách tên hàm và tên cặp từ nhãn."""

    def test_function_name_from_curve_and_implicit_labels(self) -> None:
        """Nhãn explicit, nhãn ẩn đều cho đúng tên hàm."""
        from graph_app.plotting import function_name

        assert function_name("f1(x) = sin(x)") == "f1"
        assert function_name("f2: x^2 + y^2 = 25") == "f2"
        assert function_name("f3: sin(x) = cos(y)") == "f3"

    def test_pair_functions_splits_both_names(self) -> None:
        """Cặp cho đúng hai tên hàm."""
        from graph_app.plotting import pair_functions

        assert pair_functions("f1 ∩ f4") == frozenset({"f1", "f4"})
