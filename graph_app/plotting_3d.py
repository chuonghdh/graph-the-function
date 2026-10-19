"""Dựng biểu đồ 3D Plotly theo phong cách Dark Mode.

Một hàm chung ``build_scene_3d`` vẽ mọi thành phần của không gian 3D:

- mặt ``z = f(x, y)`` bằng ``go.Surface``;
- mặt ẩn ``F(x, y, z) = 0`` bằng ``go.Isosurface``;
- đường giao của từng cặp, mỗi cặp một trace với màu riêng (``PairCurve``).

Khi bật chế độ làm nổi bật, các mặt gốc được làm mờ và đường giao của cặp được chọn được phóng to.

Module không tính toán toán học, nhờ vậy phần vẽ có thể kiểm thử riêng.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go

from graph_app.plotting import (
    BACKGROUND_COLOR,
    DIM_OPACITY,
    GRID_COLOR,
    INTERSECTION_COLOR,
    TEXT_COLOR,
    function_name,
    pair_functions,
)
from graph_app.surface import SpacePolyline, Surface

COLORSCALES: tuple[str, ...] = ("Viridis", "Plasma", "Turbo", "Electric")
"""Các bảng màu được phép cho mặt 3D. Đều hoạt động tốt trên nền tối."""

SURFACE_OPACITY: float = 0.9
"""Độ mờ của mặt ``z = f(x, y)`` khi không làm nổi bật."""

COLORBAR_STEP: float = 0.09
"""Khoảng cách ngang giữa các thanh màu của các mặt, đủ để tiêu đề ngắn không đè lên nhau."""

ISOSURFACE_OPACITY: float = 0.85
"""Độ mờ của mặt ẩn khi không làm nổi bật."""

SURFACE_DIM_OPACITY: float = DIM_OPACITY
"""Độ mờ của mặt gốc khi chế độ làm nổi bật đang bật. Rất trong suốt để đường giao vẫn hiện rõ."""

CURVE_WIDTH: int = 6
"""Độ dày đường giao bình thường."""

CURVE_FOCUS_WIDTH: int = 14
"""Độ dày đường giao khi được làm nổi bật, đủ để phóng to rõ rệt so với nền."""

DEFAULT_Z_RANGE: tuple[float, float] = (-10.0, 10.0)
"""Khoảng z mặc định khi không có giá trị hữu hạn nào để tính khung tự động."""

_Z_PERCENTILES: tuple[float, float] = (1.0, 99.0)
"""Phân vị dùng để xác định khung z tự động. Cắt 1% đầu cuối để đỉnh nhọn không làm mặt còn lại bị thu nhỏ."""

_Z_PADDING: float = 0.1
"""Phần đệm hai đầu khung z, tính theo tỉ lệ chiều cao."""

_HEIGHT_PX: int = 620
"""Chiều cao biểu đồ 3D, tính theo pixel."""


@dataclass(frozen=True)
class ImplicitSurface:
    """Một mặt ẩn ``F(x, y, z) = 0`` đã tính trên lưới 3D.

    Attributes:
        label: Tên hiển thị, ví dụ ``"f1: x^2 + y^2 + z^2 = 25"``.
        colorscale: Tên bảng màu của mặt.
        xs: Vector x của lưới.
        ys: Vector y của lưới.
        zs: Vector z của lưới.
        values: Giá trị ``F`` trên lưới, hình dạng ``(len(xs), len(ys), len(zs))``.
    """

    label: str
    colorscale: str
    xs: np.ndarray
    ys: np.ndarray
    zs: np.ndarray
    values: np.ndarray


@dataclass(frozen=True)
class PairCurve:
    """Toàn bộ đường giao của một cặp phương trình, gộp thành một trace.

    Attributes:
        label: Nhãn cặp, ví dụ ``"f1 ∩ f2"``. Cũng là tên trace trong chú thích.
        color: Màu riêng của cặp.
        points: Mảng ``(n, 3)``, các đoạn cách nhau bằng hàng ``NaN``.
    """

    label: str
    color: str
    points: np.ndarray


def compute_z_range(surfaces: list[Surface], curves: list[SpacePolyline]) -> tuple[float, float]:
    """Tính khung z tự động, bỏ qua các đỉnh cực đoan.

    Args:
        surfaces: Các mặt cần vẽ.
        curves: Các đường giao cần vẽ.

    Returns:
        Cặp ``(z_min, z_max)`` đã có phần đệm.
    """
    parts = [s.zs[np.isfinite(s.zs)] for s in surfaces]
    parts += [c.points[:, 2][np.isfinite(c.points[:, 2])] for c in curves]
    values = np.concatenate(parts) if parts else np.empty(0)
    if values.size == 0:
        return DEFAULT_Z_RANGE

    z_low, z_high = (float(v) for v in np.percentile(values, _Z_PERCENTILES))
    span = z_high - z_low
    if span <= 0:
        # Mặt phẳng nằm ngang hoặc hằng số: mở khung quanh giá trị đó để trục không suy biến.
        return z_low - 1.0, z_low + 1.0
    padding = span * _Z_PADDING
    return z_low - padding, z_high + padding


def build_figure_3d(
    surfaces: list[Surface],
    curves: list[SpacePolyline],
    surface_colorscales: list[str],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
) -> go.Figure:
    """Dựng biểu đồ chỉ gồm các mặt ``z = f(x, y)`` và đường giao, với khung z tự động.

    Args:
        surfaces: Các mặt cần vẽ.
        curves: Các đường giao cần đánh dấu, gộp thành một cặp có nhãn chung.
        surface_colorscales: Tên bảng màu cho từng mặt, cùng thứ tự với ``surfaces``.
        x_range: Khoảng trục x.
        y_range: Khoảng trục y.

    Returns:
        Biểu đồ Plotly 3D.

    Raises:
        ValueError: Khi số bảng màu không khớp số mặt.
    """
    pair_curves = (
        [PairCurve(label="Đường giao", color=INTERSECTION_COLOR, points=_merge_polylines([c.points for c in curves]))]
        if curves
        else []
    )
    return build_scene_3d(
        surfaces=surfaces,
        surface_colorscales=surface_colorscales,
        isosurfaces=[],
        pair_curves=pair_curves,
        x_range=x_range,
        y_range=y_range,
        z_range=compute_z_range(surfaces, curves),
    )


def build_scene_3d(
    surfaces: list[Surface],
    surface_colorscales: list[str],
    isosurfaces: list[ImplicitSurface],
    pair_curves: list[PairCurve],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    z_range: tuple[float, float],
    focus_pairs: frozenset[str] | None = None,
    dimmed_names: frozenset[str] = frozenset(),
) -> go.Figure:
    """Dựng một cảnh 3D duy nhất gồm mặt tường minh, mặt ẩn và đường giao theo cặp.

    Args:
        surfaces: Các mặt ``z = f(x, y)``.
        surface_colorscales: Bảng màu cho từng mặt tường minh, cùng thứ tự với ``surfaces``.
        isosurfaces: Các mặt ẩn ``F = 0``.
        pair_curves: Đường giao của từng cặp, mỗi cặp một màu.
        x_range: Khoảng trục x.
        y_range: Khoảng trục y.
        z_range: Khoảng trục z.
        focus_pairs: Các cặp cần làm nổi bật. ``None`` nghĩa là không làm nổi bật.
            Khi có giá trị, mặt gốc bị làm mờ, đường của cặp không được chọn bị làm mờ,
            và đường của cặp được chọn phóng to.
        dimmed_names: Tên các hàm bị bỏ tích ở thanh legend. Mặt của hàm đó và mọi cặp có
            liên quan đến hàm đó được làm mờ.

    Returns:
        Biểu đồ Plotly 3D, xoay được, phóng to được, và hiện tọa độ khi di chuột.

    Raises:
        ValueError: Khi số bảng màu không khớp số mặt tường minh.
    """
    if len(surface_colorscales) != len(surfaces):
        raise ValueError("Mỗi mặt cần đúng một bảng màu.")

    focus = focus_pairs is not None

    def surface_opacity(label: str) -> float:
        """Độ mờ của một mặt: mờ khi đang làm nổi bật hoặc khi hàm của mặt bị bỏ tích."""
        dimmed = focus or function_name(label) in dimmed_names
        return SURFACE_DIM_OPACITY if dimmed else SURFACE_OPACITY

    fig = go.Figure()
    for index, (surface, colorscale) in enumerate(zip(surfaces, surface_colorscales, strict=True)):
        opacity = surface_opacity(surface.label)
        fig.add_trace(_surface_trace(surface, colorscale, opacity, colorbar_x=1.0 + COLORBAR_STEP * index))
    for iso in isosurfaces:
        opacity = SURFACE_DIM_OPACITY if focus or function_name(iso.label) in dimmed_names else ISOSURFACE_OPACITY
        fig.add_trace(_isosurface_trace(iso, opacity))

    for pair in pair_curves:
        fig.add_trace(_pair_curve_trace(pair, focus, focus_pairs, dimmed_names))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", color=TEXT_COLOR),
        height=_HEIGHT_PX,
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False,
        scene=_scene_layout(x_range, y_range, z_range),
    )
    return fig


def _surface_trace(surface: Surface, colorscale: str, opacity: float, colorbar_x: float) -> go.Surface:
    """Tạo trace ``go.Surface`` cho một mặt ``z = f(x, y)``.

    Thanh màu chỉ ghi tên ngắn ``f1``, ``f2``, và được đặt ở vị trí riêng để không chồng nhau.
    Biểu thức đầy đủ vẫn hiện khi di chuột vào mặt.
    """
    short_name = surface.label.split(":", 1)[0]
    return go.Surface(
        x=surface.xs,
        y=surface.ys,
        z=surface.zs,
        colorscale=colorscale,
        opacity=opacity,
        name=surface.label,
        showscale=True,
        colorbar=dict(title=dict(text=short_name), x=colorbar_x, len=0.6, thickness=14),
        hovertemplate=f"{surface.label}<br>x=%{{x:.4f}}<br>y=%{{y:.4f}}<br>z=%{{z:.4f}}<extra></extra>",
        lighting=dict(ambient=0.7, diffuse=0.8, specular=0.2),
    )


def _isosurface_trace(iso: ImplicitSurface, opacity: float) -> go.Isosurface:
    """Tạo trace ``go.Isosurface`` cho một mặt ẩn, lấy mức 0 của ``F``.

    Tọa độ được làm tròn để giảm kích thước dữ liệu gửi lên trình duyệt.
    """
    grid_x, grid_y, grid_z = np.meshgrid(iso.xs, iso.ys, iso.zs, indexing="ij")
    return go.Isosurface(
        x=np.round(grid_x, 4).ravel(),
        y=np.round(grid_y, 4).ravel(),
        z=np.round(grid_z, 4).ravel(),
        value=np.round(iso.values, 6).ravel(),
        isomin=0.0,
        isomax=0.0,
        surface_count=1,
        colorscale=iso.colorscale,
        opacity=opacity,
        caps=dict(x_show=False, y_show=False, z_show=False),
        name=iso.label,
        showscale=False,
        hovertemplate=f"{iso.label}<extra></extra>",
        lighting=dict(ambient=0.6, diffuse=0.8, specular=0.3),
    )


ISOLATED_MARKER_PX: int = 9
"""Kích thước marker cho điểm cô lập (điểm tiếp xúc), tính theo pixel."""


def _isolated_points(points: np.ndarray) -> np.ndarray:
    """Mặt nạ các điểm đứng một mình giữa hai hàng NaN, tức điểm tiếp xúc không thuộc đường nào."""
    valid = np.isfinite(points).all(axis=1)
    prev_valid = np.concatenate([[False], valid[:-1]])
    next_valid = np.concatenate([valid[1:], [False]])
    return valid & ~prev_valid & ~next_valid


def _pair_curve_trace(
    pair: PairCurve,
    focus: bool,
    focus_pairs: frozenset[str] | None,
    dimmed_names: frozenset[str],
) -> go.Scatter3d:
    """Tạo trace đường giao của một cặp, với độ dày và độ mờ theo trạng thái làm nổi bật.

    Args:
        pair: Đường giao của cặp.
        focus: ``True`` nếu chế độ làm nổi bật đang bật.
        focus_pairs: Các cặp được chọn để làm nổi bật.

    Returns:
        Trace ``Scatter3d`` kiểu đường.
    """
    highlighted = (not focus or (focus_pairs is not None and pair.label in focus_pairs)) and not (
        pair_functions(pair.label) & dimmed_names
    )
    width = CURVE_FOCUS_WIDTH if focus and highlighted else CURVE_WIDTH
    opacity = 1.0 if highlighted else DIM_OPACITY + 0.1
    return go.Scatter3d(
        x=pair.points[:, 0],
        y=pair.points[:, 1],
        z=pair.points[:, 2],
        mode="lines+markers",
        name=pair.label,
        line=dict(color=pair.color, width=width),
        marker=dict(
            size=np.where(_isolated_points(pair.points), ISOLATED_MARKER_PX, 0),
            color=pair.color,
        ),
        showlegend=False,
        opacity=opacity,
        hovertemplate=f"{pair.label}<br>x=%{{x:.4f}}<br>y=%{{y:.4f}}<br>z=%{{z:.4f}}<extra></extra>",
    )


def _merge_polylines(polylines: list[np.ndarray]) -> np.ndarray:
    """Nối nhiều đường gấp khúc thành một mảng, ngăn cách bằng hàng ``NaN``.

    Args:
        polylines: Danh sách mảng ``(n, 3)``.

    Returns:
        Mảng ``(m, 3)``, rỗng nếu không có điểm nào.
    """
    blocks = [p for p in polylines if p.size]
    if not blocks:
        return np.empty((0, 3))
    gap = np.full((1, 3), np.nan)
    pieces: list[np.ndarray] = []
    for block in blocks:
        pieces.extend([block, gap])
    return np.vstack(pieces)


def _scene_layout(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    z_range: tuple[float, float],
) -> dict[str, object]:
    """Tạo cấu hình ba trục cho không gian 3D với nền tối.

    Args:
        x_range: Khoảng trục x.
        y_range: Khoảng trục y.
        z_range: Khoảng trục z.

    Returns:
        Dict cấu hình ``scene`` của Plotly.
    """
    axis_style = dict(
        backgroundcolor=BACKGROUND_COLOR,
        gridcolor=GRID_COLOR,
        zerolinecolor="#4A4F5C",
        showbackground=True,
    )
    return dict(
        xaxis=dict(title="x", range=list(x_range), **axis_style),
        yaxis=dict(title="y", range=list(y_range), **axis_style),
        zaxis=dict(title="z", range=list(z_range), **axis_style),
        aspectmode="cube",
        bgcolor="rgba(0, 0, 0, 0)",
    )
