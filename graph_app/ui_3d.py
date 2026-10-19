"""Giao diện đồ thị 3D: một cảnh chung cho mặt ``z = f(x, y)``, mặt ẩn, đường giao và chế độ làm nổi bật.

Module chỉ được gọi khi có ít nhất một phương trình chứa ``z``. Các phương trình 2D trong cùng
cảnh được vẽ thành mặt trụ đứng, vì đó là đúng hình học của chúng trong không gian ba chiều.

Quy ước lưới:

- Mặt tường minh ``z = f(x, y)`` dùng lưới 2D với độ phân giải người dùng chọn.
- Mặt ẩn và đường giao dùng lưới 3D với độ phân giải bị chặn ở ``GRID_3D_MAX``.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import streamlit as st

from graph_app.equations import UserEquation
from graph_app.implicit import GRID_3D_MAX, implicit_surface_intersection, isosurface_grid
from graph_app.plotting import pair_color
from graph_app.plotting_3d import ImplicitSurface, PairCurve, build_scene_3d
from graph_app.refine import isolated_tangencies
from graph_app.surface import Surface, evaluate_surface, intersection_curves
from graph_app.ui_focus import PairRow, render_pair_rows, system_text
from graph_app.ui_sidebar import SidebarState
from graph_app.viewport import domain_for


def render_3d(
    equations: dict[int, UserEquation],
    state: SidebarState,
    dimmed_names: frozenset[str] = frozenset(),
) -> None:
    """Dựng cảnh 3D gồm mọi phương trình, các đường giao theo cặp và chế độ làm nổi bật.

    Args:
        equations: Phương trình đã phân tích, theo chỉ số ô.
        state: Đầu vào của thanh bên, dùng cho khoảng trục, độ phân giải và bảng màu.
    """
    if not equations:
        st.info("Nhập ít nhất một phương trình ở thanh bên để bắt đầu vẽ.")
        return
    if not _ranges_valid(state):
        st.error("Cận dưới của mỗi trục phải nhỏ hơn cận trên.")
        return

    domain_x, domain_y, domain_z = domain_for(state.x_range), domain_for(state.y_range), domain_for(state.z_range)
    # Mặt tường minh dùng lưới dày hơn vì miền đã mở rộng gấp ba, nhưng vẫn bị chặn để gọn dữ liệu.
    surface_res = min(state.resolution * 3, MAX_SURFACE_GRID)
    xs_surface = np.linspace(*domain_x, surface_res)
    ys_surface = np.linspace(*domain_y, surface_res)
    surfaces = _explicit_surfaces(equations, xs_surface, ys_surface)

    # Lưới 3D chỉ cần khi có phương trình không phải z = f(x, y). Hai mặt tường minh
    # cắt nhau đã có thuật toán riêng trên lưới 2D.
    needs_volume = any(not eq.is_explicit_z for eq in equations.values())
    xs_vol = ys_vol = zs_vol = np.empty(0)
    values: dict[int, np.ndarray] = {}
    if needs_volume:
        vol_res = min(state.resolution, GRID_3D_MAX)
        xs_vol = np.linspace(*domain_x, vol_res)
        ys_vol = np.linspace(*domain_y, vol_res)
        zs_vol = np.linspace(*domain_z, vol_res)
        values = {i: isosurface_grid(eq.implicit_3d, xs_vol, ys_vol, zs_vol) for i, eq in equations.items()}

    isosurfaces = [
        ImplicitSurface(
            label=f"f{i + 1}: {eq.text}",
            colorscale=state.colorscales[i],
            xs=xs_vol,
            ys=ys_vol,
            zs=zs_vol,
            values=values[i],
        )
        for i, eq in sorted(equations.items())
        if not eq.is_explicit_z
    ]

    pair_curves, summary = _pair_curves(equations, surfaces, values, (xs_vol, ys_vol, zs_vol))

    # Đồ thị nằm phía trên nhưng cần trạng thái checkbox bên dưới, nên tạo khung trước rồi điền sau.
    chart_box = st.container()
    focus_pairs = _render_summary(summary)
    figure = build_scene_3d(
        surfaces=list(surfaces.values()),
        surface_colorscales=[state.colorscales[i] for i in sorted(surfaces)],
        isosurfaces=isosurfaces,
        pair_curves=pair_curves,
        x_range=state.x_range,
        y_range=state.y_range,
        z_range=state.z_range,
        focus_pairs=focus_pairs,
        dimmed_names=dimmed_names,
    )
    with chart_box:
        st.plotly_chart(figure, config={"displaylogo": False})



MAX_SURFACE_GRID: int = 200
"""Số điểm tối đa mỗi chiều của mặt tường minh, để dữ liệu gửi lên trình duyệt không quá lớn."""


def _ranges_valid(state: SidebarState) -> bool:
    """Kiểm tra cận dưới nhỏ hơn cận trên trên mọi trục."""
    return all(low < high for low, high in (state.x_range, state.y_range, state.z_range))


def _explicit_surfaces(
    equations: dict[int, UserEquation],
    xs: np.ndarray,
    ys: np.ndarray,
) -> dict[int, Surface]:
    """Tính lưới Z cho mọi phương trình ``z = f(x, y)``.

    Args:
        equations: Phương trình đã phân tích.
        xs: Vector x của lưới mặt.
        ys: Vector y của lưới mặt.

    Returns:
        Ánh xạ chỉ số ô sang ``Surface``, chỉ gồm các phương trình tường minh.
    """
    return {
        i: Surface(label=f"f{i + 1}: {eq.text}", xs=xs, ys=ys, zs=evaluate_surface(eq.func, xs, ys))
        for i, eq in sorted(equations.items())
        if eq.is_explicit_z
    }


def _pair_curves(
    equations: dict[int, UserEquation],
    surfaces: dict[int, Surface],
    values: dict[int, np.ndarray],
    grid: tuple[np.ndarray, np.ndarray, np.ndarray],
) -> tuple[list[PairCurve], list[tuple[str, str, str, int]]]:
    """Tính đường giao cho mọi cặp và gộp mỗi cặp thành một ``PairCurve`` có màu riêng.

    Hai mặt tường minh dùng thuật toán theo lưới 2D cho chính xác. Mọi cặp còn lại dùng thuật
    toán theo voxel trên lưới 3D.

    Args:
        equations: Phương trình đã phân tích.
        surfaces: Mặt tường minh đã tính, theo chỉ số ô.
        values: Giá trị ``F`` trên lưới 3D, theo chỉ số ô. Rỗng nếu không cần lưới 3D.
        grid: Ba vector ``(xs, ys, zs)`` của lưới 3D.

    Returns:
        Cặp ``(pair_curves, summary)``. ``summary`` gồm ``(nhãn cặp, văn bản A, văn bản B, số đoạn)``.
    """
    xs, ys, zs = grid
    pair_curves: list[PairCurve] = []
    summary: list[tuple[str, str, str, int]] = []
    for i, j in combinations(sorted(equations), 2):
        label = f"f{i + 1} ∩ f{j + 1}"
        if i in surfaces and j in surfaces:
            polylines = [
                c.points
                for c in intersection_curves(surfaces[i], surfaces[j], equations[i].func, equations[j].func)
            ]
        else:
            first, second = equations[i].implicit_3d, equations[j].implicit_3d
            polylines = list(
                implicit_surface_intersection(values[i], values[j], xs, ys, zs, refine_with=(first, second))
            )
            # Điểm tiếp xúc không nằm trên đoạn nào, nên thêm như khối một điểm để vẽ marker.
            tangents = isolated_tangencies(first, second, xs, ys, zs, values[i], values[j])
            polylines += [point.reshape(1, 3) for point in tangents]
        pair_curves.append(PairCurve(label=label, color=pair_color(label), points=_merged(polylines)))
        summary.append((label, equations[i].text, equations[j].text, len(polylines)))
    return pair_curves, summary


def _merged(polylines: list[np.ndarray]) -> np.ndarray:
    """Nối nhiều đoạn hoặc đường thành một mảng ``(n, 3)``, ngăn cách bằng hàng ``NaN``.

    Args:
        polylines: Danh sách mảng ``(k, 3)``, hoặc các đoạn ``(2, 3)``.

    Returns:
        Mảng gộp, rỗng nếu không có điểm nào.
    """
    blocks = [np.asarray(p).reshape(-1, 3) for p in polylines if np.size(p)]
    if not blocks:
        return np.empty((0, 3))
    gap = np.full((1, 3), np.nan)
    pieces: list[np.ndarray] = []
    for block in blocks:
        pieces.extend([block, gap])
    return np.vstack(pieces)


def _render_summary(summary: list[tuple[str, str, str, int]]) -> frozenset[str] | None:
    """Hiển thị một hàng cho mỗi cặp, có checkbox làm nổi bật và hệ phương trình giao tuyến.

    Args:
        summary: ``(nhãn cặp, văn bản A, văn bản B, số đoạn)`` của từng cặp.

    Returns:
        Tập các cặp đang được tích, hoặc ``None`` nếu không có cặp nào được tích.
    """
    if not summary:
        return None
    st.subheader("Đường giao giữa các mặt")
    rows = []
    for pair, first, second, count in summary:
        if count:
            text = system_text(first, second)
        else:
            text = "không có đường giao trong khoảng đã chọn."
        rows.append(PairRow(pair=pair, text=text, has_result=count > 0))
    return render_pair_rows(rows)
