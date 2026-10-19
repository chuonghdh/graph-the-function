"""Giao diện đồ thị 2D: vẽ các phương trình 2D, giao điểm, chế độ làm nổi bật và bảng tọa độ.

Module chỉ được gọi khi toàn bộ hệ thống là 2D, nên mọi phương trình đều không chứa ``z``.
Thanh bên, ô nhập và việc nhận diện chiều nằm ở ``ui_sidebar`` và ``app``.

Thứ tự tính: giao điểm được tìm trước trên miền dò, sau đó khung x (nếu tự canh) được canh để
chứa mọi giao điểm, rồi khung y được canh theo đồ thị và giao điểm. Khung không được đặt trước
khi chưa biết giao điểm.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import combinations

import numpy as np
import streamlit as st

from graph_app.equations import UserEquation
from graph_app.implicit import find_implicit_intersections, implicit_curve_polylines
from graph_app.math_engine import Intersection, ParsedFunction, find_intersections, sample_function
from graph_app.plotting import PALETTE, Curve, IntersectionMarker, build_figure, compute_y_range
from graph_app.ui_focus import PairRow, render_pair_rows
from graph_app.ui_sidebar import DEFAULT_XY_RANGE, SidebarState
from graph_app.viewport import domain_for, fit_view, samples_for

SEARCH_HALF_WIDTH: float = 200.0
"""Nửa độ rộng cửa sổ dò giao điểm khi khung tự canh. Giao điểm xa hơn ±200 sẽ không được tìm."""

SEARCH_DENSITY: float = 250.0
"""Số mẫu mỗi đơn vị khi dò giao điểm. Dày hơn đường vẽ để không bỏ sót nghiệm của hàm dao động nhanh."""

SEARCH_MAX_SAMPLES: int = 100_000
"""Giới hạn số mẫu khi dò giao điểm một biến. Cao hơn mức này thì thời gian tính vượt ngân sách."""

FRAME_PASSES: int = 4
"""Số lượt tối đa vẽ lại đường ẩn khi khung y tự canh vượt miền đã vẽ. Bốn lượt đủ cho các đường thường gặp."""

MAX_LISTED_POINTS: int = 50
"""Số giao điểm tối đa được liệt kê tọa độ trong dòng kết quả của một cặp."""

MAX_TABLE_ROWS: int = 500
"""Số dòng tối đa của bảng tọa độ. Trên mức này chỉ hiện số lượng."""

SEARCH_GRID_MAX: int = 1200
"""Giới hạn số ô lưới mỗi chiều khi dò giao điểm ẩn trên cửa sổ rộng."""

CURVE_DENSITY: float = 300.0
"""Số điểm mỗi đơn vị độ rộng khi lấy mẫu ``y = g(x)``. Giữ mật độ không đổi khi zoom."""

CURVE_MIN_SAMPLES: int = 1500
CURVE_MAX_SAMPLES: int = 8000
"""Giới hạn số điểm cho một đường ``y = g(x)``. Trên mức này trình duyệt không cần thêm chi tiết."""

GRID_DENSITY: float = 60.0
GRID_MIN_SAMPLES: int = 300
GRID_MAX_SAMPLES: int = 600
"""Mật độ và giới hạn lưới cho đường ẩn và giao điểm ẩn."""


@dataclass(frozen=True)
class PairResult:
    """Kết quả giao của một cặp phương trình, đã lọc theo khung nhìn.

    Attributes:
        pair: Nhãn cặp, ví dụ ``"f1 ∩ f2"``.
        first: Chỉ số ô của phương trình thứ nhất.
        second: Chỉ số ô của phương trình thứ hai.
        points: Các giao điểm nằm trong khung nhìn.
    """

    pair: str
    first: int
    second: int
    points: list[Intersection]


def render_2d(
    equations: dict[int, UserEquation],
    state: SidebarState,
    dimmed_names: frozenset[str] = frozenset(),
) -> None:
    """Dựng đồ thị 2D: giao điểm, công tắc làm nổi bật, đồ thị và bảng tọa độ.

    Args:
        equations: Phương trình đã phân tích, theo chỉ số ô. Mọi phương trình đều là 2D.
        state: Đầu vào của thanh bên. Khung x và y được tự canh theo giao điểm khi bật; khi tắt
            thì dùng đúng khoảng người dùng nhập.
        dimmed_names: Tên các hàm đang bị bỏ tích ở thanh legend.
    """
    if not equations:
        st.info("Nhập ít nhất một phương trình ở thanh bên để bắt đầu vẽ.")
        return

    # Thứ tự quan trọng: tính giao điểm trước, rồi mới canh khung. Khung không được đặt trước
    # để chứa giao điểm, vì khi đó giao điểm nằm ngoài khung sẽ bị mất.
    search_x = _search_window(state.x_auto, state.x_range)
    search_y = _search_window(state.y_auto, state.y_range)
    pair_results = _pair_results(equations, search_x, search_y)

    # Khung y tự canh thì mọi giao điểm trong khung x đều được giữ, vì khung y sẽ bao lấy chúng.
    view_y = None if state.y_auto else state.y_range
    if state.x_auto:
        view_x = fit_view(_xs_in_view_y(pair_results, view_y), DEFAULT_XY_RANGE)
    else:
        view_x = state.x_range

    results = [_restrict_to_view(result, view_x, view_y) for result in pair_results]
    markers = [IntersectionMarker(pair=r.pair, point=p) for r in results for p in r.points]

    # Đường vẽ được tính sau khi biết khung x, trên miền nhỏ quanh khung, nên đường ẩn mịn khi xem
    # gần. Khung y tự canh chỉ biết sau khi có đường. Nếu khung vượt miền đã vẽ thì vẽ lại trên khung
    # mới, để đường ẩn không bị cắt phẳng (ví dụ đường tròn bán kính 50 khi miền y chỉ tới 18).
    draw_y = view_y if view_y is not None else fit_view(_ys_in_view(pair_results, view_x), DEFAULT_XY_RANGE)
    for _ in range(FRAME_PASSES):
        curves = _build_curves(equations, domain_for(view_x), domain_for(draw_y))
        if view_y is not None:
            frame = view_y
            break
        frame = compute_y_range(_clip_to_view(curves, view_x), markers)
        if _covers(domain_for(draw_y), frame):
            break
        draw_y = frame

    # Đồ thị nằm phía trên nhưng cần trạng thái checkbox bên dưới, nên tạo khung trước rồi điền sau.
    chart_box = st.container()
    focus_pairs = _render_result_rows(results)
    figure = build_figure(
        curves,
        markers,
        view_x,
        frame,
        focus_pairs=focus_pairs,
        dimmed_names=dimmed_names,
    )
    with chart_box:
        st.plotly_chart(figure, config={"displaylogo": False})

    _render_intersection_table(markers)


def _build_curves(
    equations: dict[int, UserEquation],
    domain_x: tuple[float, float],
    domain_y: tuple[float, float],
) -> list[Curve]:
    """Tạo đường vẽ cho từng phương trình trên miền tính toán mở rộng.

    Args:
        equations: Phương trình đã phân tích, theo chỉ số ô.
        domain_x: Miền x mở rộng.
        domain_y: Miền y mở rộng, làm lưới cho đường ẩn.

    Returns:
        Danh sách ``Curve`` theo thứ tự chỉ số ô tăng dần.
    """
    curves: list[Curve] = []
    x_span = domain_x[1] - domain_x[0]
    samples = samples_for(x_span, CURVE_DENSITY, CURVE_MIN_SAMPLES, CURVE_MAX_SAMPLES)
    grid = _grid_size(domain_x, domain_y)
    for index in sorted(equations):
        equation = equations[index]
        color = PALETTE[index]
        name = f"f{index + 1}"
        if equation.is_explicit_y:
            x, y = sample_function(equation.func, domain_x[0], domain_x[1], samples)
            curves.append(Curve(label=f"{name}(x) = {equation.text}", color=color, x=x, y=y, cut_jumps=True))
        else:
            xs, ys = _implicit_polyline_arrays(equation, domain_x, domain_y, grid)
            curves.append(Curve(label=f"{name}: {equation.text}", color=color, x=xs, y=ys, cut_jumps=False))
    return curves


def _grid_size(domain_x: tuple[float, float], domain_y: tuple[float, float]) -> int:
    """Số điểm mỗi chiều của lưới 2D, theo cạnh dài hơn của miền tính toán."""
    span = max(domain_x[1] - domain_x[0], domain_y[1] - domain_y[0])
    return samples_for(span, GRID_DENSITY, GRID_MIN_SAMPLES, GRID_MAX_SAMPLES)


def _implicit_polyline_arrays(
    equation: UserEquation,
    domain_x: tuple[float, float],
    domain_y: tuple[float, float],
    grid: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Gộp các đường mức của phương trình ẩn thành một mảng, ngăn cách bằng ``NaN``.

    Args:
        equation: Phương trình ẩn 2D.
        domain_x: Miền x mở rộng.
        domain_y: Miền y mở rộng.
        grid: Số điểm mỗi chiều của lưới.

    Returns:
        Cặp mảng ``(x, y)``. Rỗng nếu đường không đi qua miền.
    """
    lines = implicit_curve_polylines(_implicit_2d(equation), domain_x, domain_y, samples=grid)
    if not lines:
        return np.empty(0), np.empty(0)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    gap = np.array([np.nan])
    for line in lines:
        xs.extend([line[:, 0], gap])
        ys.extend([line[:, 1], gap])
    return np.concatenate(xs), np.concatenate(ys)


def _pair_results(
    equations: dict[int, UserEquation],
    domain_x: tuple[float, float],
    domain_y: tuple[float, float],
) -> list[PairResult]:
    """Tìm giao điểm của mọi cặp phương trình trên miền tính toán mở rộng.

    Cặp gồm hai hàm ``y = g(x)`` dùng thuật toán một biến cho chính xác và nhanh.
    Các cặp còn lại dùng thuật toán hai biến trên dạng ``F(x, y) = 0``.

    Args:
        equations: Phương trình đã phân tích, theo chỉ số ô.
        domain_x: Miền x mở rộng.
        domain_y: Miền y mở rộng.

    Returns:
        Danh sách ``PairResult`` theo thứ tự cặp. Cặp không có giao điểm vẫn có mặt với danh sách rỗng.
    """
    results: list[PairResult] = []
    for i, j in combinations(sorted(equations), 2):
        points = _intersections_for_pair(equations[i], equations[j], domain_x, domain_y)
        results.append(PairResult(pair=f"f{i + 1} ∩ f{j + 1}", first=i, second=j, points=points))
    return results


def _intersections_for_pair(
    first: UserEquation,
    second: UserEquation,
    domain_x: tuple[float, float],
    domain_y: tuple[float, float],
) -> list[Intersection]:
    """Chọn thuật toán giao điểm phù hợp cho một cặp phương trình.

    Args:
        first: Phương trình thứ nhất.
        second: Phương trình thứ hai.
        domain_x: Miền x mở rộng.
        domain_y: Miền y mở rộng.

    Returns:
        Danh sách giao điểm của cặp.
    """
    if first.is_explicit_y and second.is_explicit_y:
        samples = samples_for(
            domain_x[1] - domain_x[0], SEARCH_DENSITY, CURVE_MIN_SAMPLES, SEARCH_MAX_SAMPLES
        )
        return find_intersections(first.func, second.func, domain_x[0], domain_x[1], samples)
    span = max(domain_x[1] - domain_x[0], domain_y[1] - domain_y[0])
    grid = samples_for(span, SEARCH_DENSITY, GRID_MIN_SAMPLES, SEARCH_GRID_MAX)
    return find_implicit_intersections(
        _implicit_2d(first),
        _implicit_2d(second),
        domain_x,
        domain_y,
        samples=grid,
    )


def _search_window(auto: bool, view: tuple[float, float]) -> tuple[float, float]:
    """Miền dò giao điểm và vẽ đường cong trên một trục.

    Khi trục tự canh, khung chưa biết trước nên dò trên cửa sổ cố định ``±SEARCH_HALF_WIDTH``.
    Khi trục cố định, dò trên khung người dùng chọn, mở rộng để zoom out vẫn có nhánh đồ thị.

    Args:
        auto: ``True`` nếu trục đang tự canh.
        view: Khoảng người dùng nhập cho trục.

    Returns:
        Khoảng ``(min, max)`` dùng làm miền tính toán.
    """
    if auto:
        return -SEARCH_HALF_WIDTH, SEARCH_HALF_WIDTH
    return domain_for(view)


def _xs_in_view_y(results: list[PairResult], view_y: tuple[float, float] | None) -> list[float]:
    """Hoành độ mọi giao điểm, chỉ tính các điểm nằm trong khoảng y nếu có.

    Args:
        results: Kết quả giao của các cặp trên miền dò.
        view_y: Khoảng y cố định, hoặc ``None`` khi y tự canh (mọi điểm đều được tính).

    Returns:
        Danh sách hoành độ, dùng để canh khung x.
    """
    xs: list[float] = []
    for result in results:
        for point in result.points:
            if view_y is None or view_y[0] <= point.y <= view_y[1]:
                xs.append(point.x)
    return xs


def _covers(outer: tuple[float, float], inner: tuple[float, float]) -> bool:
    """``True`` nếu khoảng ``outer`` bao trọn khoảng ``inner``."""
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _ys_in_view(results: list[PairResult], view_x: tuple[float, float]) -> list[float]:
    """Tung độ mọi giao điểm nằm trong khoảng x cho trước, dùng để canh khung y của đường vẽ.

    Args:
        results: Kết quả giao của các cặp trên miền dò.
        view_x: Khoảng x của khung nhìn.

    Returns:
        Danh sách tung độ.
    """
    return [p.y for r in results for p in r.points if view_x[0] <= p.x <= view_x[1]]


def _restrict_to_view(
    result: PairResult,
    view_x: tuple[float, float],
    view_y: tuple[float, float] | None,
) -> PairResult:
    """Giữ lại các giao điểm nằm trong khung nhìn. Điểm ngoài khung không được vẽ hay liệt kê.

    Args:
        result: Kết quả giao của một cặp trên miền dò.
        view_x: Khoảng x của khung nhìn.
        view_y: Khoảng y cố định, hoặc ``None`` khi y tự canh (không lọc theo y).

    Returns:
        ``PairResult`` mới chỉ chứa các điểm trong khung nhìn.
    """
    inside = [
        p
        for p in result.points
        if view_x[0] <= p.x <= view_x[1] and (view_y is None or view_y[0] <= p.y <= view_y[1])
    ]
    return replace(result, points=inside)


def _clip_to_view(curves: list[Curve], view_x: tuple[float, float]) -> list[Curve]:
    """Bản sao các đường với giá trị y bị đặt thành NaN ngoài khung x. Dùng để tính khung y tự động.

    Args:
        curves: Các đường trên miền mở rộng.
        view_x: Khoảng x của khung nhìn.

    Returns:
        Danh sách ``Curve`` chỉ còn dữ liệu trong khung x.
    """
    clipped: list[Curve] = []
    for curve in curves:
        outside = (curve.x < view_x[0]) | (curve.x > view_x[1])
        y = np.where(outside, np.nan, curve.y)
        clipped.append(replace(curve, y=y))
    return clipped


def _implicit_2d(equation: UserEquation) -> ParsedFunction:
    """Lấy dạng ``F(x, y) = 0`` của phương trình 2D.

    Raises:
        ValueError: Khi phương trình không có dạng 2D. Không xảy ra nếu chiều đã được nhận diện đúng.
    """
    if equation.implicit_2d is None:
        raise ValueError("Phương trình này không có dạng 2D.")
    return equation.implicit_2d


def _render_result_rows(results: list[PairResult]) -> frozenset[str] | None:
    """Hiển thị hàng kết quả cho từng cặp, mỗi hàng có checkbox làm nổi bật.

    Args:
        results: Kết quả giao của các cặp, đã lọc theo khung nhìn.

    Returns:
        Tập các cặp đang được tích, hoặc ``None`` nếu không có cặp nào được tích.
    """
    st.subheader("Điểm giao nhau")
    rows = [_result_row(result) for result in results]
    return render_pair_rows(rows)


def _result_row(result: PairResult) -> PairRow:
    """Tạo nội dung hàng kết quả: danh sách tọa độ giao điểm trong khung nhìn của cặp.

    Args:
        result: Kết quả giao của một cặp.

    Returns:
        ``PairRow`` tương ứng.
    """
    if not result.points:
        return PairRow(pair=result.pair, text="không có giao điểm trong khung nhìn.", has_result=False)
    if len(result.points) > MAX_LISTED_POINTS:
        return PairRow(
            pair=result.pair,
            text=f"{len(result.points)} giao điểm (quá nhiều để liệt kê từng điểm).",
            has_result=True,
        )
    coords = ", ".join(f"({p.x:.4f}; {p.y:.4f})" for p in result.points)
    return PairRow(pair=result.pair, text=f"{len(result.points)} giao điểm: {coords}", has_result=True)


def _render_intersection_table(markers: list[IntersectionMarker]) -> None:
    """Hiển thị bảng tọa độ giao điểm trong khung nhìn.

    Args:
        markers: Danh sách giao điểm cần hiển thị.
    """
    if not markers:
        return
    if len(markers) > MAX_TABLE_ROWS:
        st.caption(f"Có {len(markers)} giao điểm, quá nhiều để hiển thị trong bảng.")
        return
    rows = [_marker_row(marker) for marker in markers]
    st.dataframe(rows, hide_index=True)


def _marker_row(marker: IntersectionMarker) -> dict[str, str | float]:
    """Chuyển một giao điểm thành dòng hiển thị trong bảng.

    Args:
        marker: Giao điểm cần chuyển đổi.

    Returns:
        Dict với các cột ``Cặp hàm``, ``x``, ``y``, làm tròn đến 4 chữ số thập phân.
    """
    point = marker.point
    return {
        "Cặp hàm": marker.pair,
        "x": round(point.x, 4),
        "y": round(point.y, 4),
    }
