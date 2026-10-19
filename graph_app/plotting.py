"""Dựng biểu đồ 2D Plotly theo Dark Mode: đường cong, điểm giao, chú thích và chế độ làm nổi bật.

Module nhận dữ liệu đã tính sẵn và trả về ``plotly.graph_objects.Figure``. Không tính toán
toán học tại đây, nhờ vậy phần vẽ có thể kiểm thử riêng.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations
from dataclasses import dataclass

import numpy as np
import plotly.graph_objects as go

from graph_app.math_engine import Intersection

PALETTE: tuple[str, ...] = (
    "#00F0FF",  # neon cyan, phương trình thứ nhất
    "#FF2BD6",  # neon magenta, phương trình thứ hai
    "#FFEA00",  # neon vàng sáng, phương trình thứ ba
    "#39FF14",  # neon xanh lá, phương trình thứ tư
    "#FF9F1C",  # neon cam, phương trình thứ năm
    "#B388FF",  # neon tím, phương trình thứ sáu
)
"""Bảng neon cho các đường cong. Số phần tử bằng số ô nhập tối đa, mỗi ô một màu không trùng."""

PAIR_PALETTE: tuple[str, ...] = (
    "#FF9F1C", "#7CFF00", "#B388FF", "#FF3D71", "#00C2FF",
    "#FFD400", "#00FFA3", "#FF7AC6", "#F15BB5", "#9B5DE5",
    "#00BBF9", "#00F5D4", "#FEE440", "#FF006E", "#8AC926",
)
"""15 màu neon, đủ cho mọi cặp của tối đa 6 hàm. Thứ tự cặp theo ``itertools.combinations``."""

PAIR_COLORS: dict[str, str] = {
    f"f{i + 1} ∩ f{j + 1}": PAIR_PALETTE[k]
    for k, (i, j) in enumerate(combinations(range(6), 2))
}
"""Màu cố định cho từng cặp giao, ví dụ ``"f1 ∩ f2"``. Khác ``PALETTE`` để giao điểm không lẫn với đường cong."""

INTERSECTION_COLOR: str = "#FFFFFF"
"""Màu dự phòng cho giao điểm thuộc cặp chưa khai báo trong ``PAIR_COLORS``."""

BACKGROUND_COLOR: str = "#0E1117"
"""Màu nền của ứng dụng, đồng bộ với ``.streamlit/config.toml``."""

GRID_COLOR: str = "#1F2430"
AXIS_COLOR: str = "#4A4F5C"
AXIS_LINE_COLOR: str = "#8B949E"
"""Màu đường trục x và y. Đủ sáng để thấy trên nền tối; đường lưới thì mờ hơn."""
ANNOTATION_BG: str = "rgba(14, 17, 23, 0.85)"
TEXT_COLOR: str = "#E6EDF3"
"""Màu chữ chính, đủ tương phản trên nền #0E1117."""

DIM_OPACITY: float = 0.15
"""Độ mờ của phần bị làm mờ ở chế độ làm nổi bật. Đủ thấy để giữ ngữ cảnh, đủ nhạt để không che phần nổi bật."""

PLOT_SIZE_PX: tuple[int, int] = (924, 494)
"""Kích thước vùng vẽ ước lượng để đặt chú thích. Khớp chiều cao 560 px trong layout."""

DEFAULT_Y_RANGE: tuple[float, float] = (-10.0, 10.0)
"""Khoảng tung độ mặc định khi không có giá trị hữu hạn nào để vẽ."""

_ASYMPTOTE_FACTOR: float = 10.0
"""Một điểm đổi dấu được coi là tiệm cận khi cả hai đầu đều lớn hơn ``_ASYMPTOTE_FACTOR`` lần độ lớn trung vị của hàm."""

_JUMP_FACTOR: float = 2.0
"""Bước nhảy giữa hai mẫu liền kề lớn hơn ``_JUMP_FACTOR`` lần chiều cao khung được coi là tiệm cận."""

_Y_PERCENTILES: tuple[float, float] = (2.0, 98.0)
"""Phân vị dùng để xác định khung tung độ. Cắt 2% đầu cuối để giá trị tiệm cận không làm méo khung."""

_Y_PADDING: float = 0.1
"""Phần đệm thêm vào hai đầu khung tung độ, tính theo tỉ lệ chiều cao."""


def function_name(label: str) -> str:
    """Tên hàm trong nhãn, ví dụ ``"f1(x) = sin(x)"`` hoặc ``"f2: x^2 + y^2 = 1"`` cho ``"f1"`` và ``"f2"``."""
    return label.split(":", 1)[0].split("(", 1)[0].strip()


def pair_functions(pair: str) -> frozenset[str]:
    """Tên hai hàm của một cặp, ví dụ ``"f1 ∩ f2"`` cho ``{"f1", "f2"}``."""
    return frozenset(part.strip() for part in pair.split("∩"))


def pair_color(pair: str) -> str:
    """Trả về màu của một cặp giao, hoặc màu dự phòng nếu cặp chưa được khai báo.

    Args:
        pair: Nhãn cặp, ví dụ ``"f1 ∩ f2"``.

    Returns:
        Mã màu dạng ``#RRGGBB``.
    """
    return PAIR_COLORS.get(pair, INTERSECTION_COLOR)


@dataclass(frozen=True)
class Curve:
    """Một đường đồ thị đã được lấy mẫu.

    Attributes:
        label: Tên hiển thị trong chú thích, ví dụ ``"f1(x) = sin(x)"``.
        color: Màu đường vẽ, lấy từ ``PALETTE``.
        x: Mảng hoành độ.
        y: Mảng tung độ, có ``NaN`` tại điểm không xác định hoặc giữa các đoạn rời nhau.
        cut_jumps: ``True`` với hàm ``y = f(x)`` để cắt tại tiệm cận. ``False`` với đường ẩn,
            vì đường đứng có bước nhảy lớn theo y nhưng vẫn liền mạch.
    """

    label: str
    color: str
    x: np.ndarray
    y: np.ndarray
    cut_jumps: bool = True


@dataclass(frozen=True)
class IntersectionMarker:
    """Một giao điểm kèm nhãn cặp hàm để hiển thị chú thích.

    Attributes:
        pair: Nhãn cặp hàm, ví dụ ``"f1 ∩ f2"``.
        point: Tọa độ giao điểm.
    """

    pair: str
    point: Intersection


def compute_y_range(
    curves: list[Curve],
    markers: list[IntersectionMarker],
) -> tuple[float, float]:
    """Tính khung tung độ hợp lý, bỏ qua các giá trị tiệm cận cực lớn.

    Dùng phân vị thay vì min/max để một đường tiệm cận như ``tan(x)`` không ép đồ thị còn lại nhỏ đi.
    Khung luôn bao gồm tung độ của mọi giao điểm.

    Args:
        curves: Các đường đồ thị cần vẽ.
        markers: Các giao điểm cần hiển thị.

    Returns:
        Cặp ``(y_min, y_max)`` đã có phần đệm.
    """
    finite_parts = [c.y[np.isfinite(c.y)] for c in curves]
    finite_values = np.concatenate(finite_parts) if finite_parts else np.empty(0)
    if finite_values.size:
        y_low, y_high = (float(v) for v in np.percentile(finite_values, _Y_PERCENTILES))
    elif markers:
        # Không có đường nào hữu hạn nhưng vẫn có giao điểm: khung bắt đầu từ điểm đó.
        y_low = y_high = markers[0].point.y
    else:
        # Không có gì để vẽ: dùng khung mặc định nguyên vẹn, không thêm phần đệm.
        return DEFAULT_Y_RANGE

    marker_ys = [m.point.y for m in markers]
    if marker_ys:
        y_low = min(y_low, min(marker_ys))
        y_high = max(y_high, max(marker_ys))

    span = float(y_high - y_low)
    if span <= 0:
        # Hàm hằng hoặc chỉ có một điểm: mở rộng khung quanh giá trị đó.
        span = 2.0
        center = float(y_low)
        return center - span / 2, center + span / 2

    padding = span * _Y_PADDING
    return float(y_low - padding), float(y_high + padding)


def break_discontinuities(y: np.ndarray, frame_height: float) -> np.ndarray:
    """Cắt đường vẽ tại các điểm gián đoạn để không nối qua tiệm cận.

    Args:
        y: Mảng tung độ đã lấy mẫu.
        frame_height: Chiều cao khung tung độ đang hiển thị.

    Returns:
        Bản sao của ``y`` với các điểm gián đoạn được thay bằng ``NaN``.
    """
    cleaned = y.astype(float, copy=True)
    jumps = np.abs(np.diff(cleaned)) > _JUMP_FACTOR * frame_height

    # Tiệm cận thứ hai: hàm đổi dấu nhưng cả hai đầu đều lớn hơn hẳn độ lớn điển hình của chính nó.
    # Một hàm liên tục chỉ đổi dấu khi đi qua gần 0. Quy tắc này không phụ thuộc khung chung,
    # nên vẫn bắt được tiệm cận khi một hàm khác làm khung rất cao (ví dụ x^5 cùng tan(x)).
    finite = np.abs(cleaned[np.isfinite(cleaned)])
    typical = float(np.median(finite)) if finite.size else 0.0
    left, right = cleaned[:-1], cleaned[1:]
    both_finite = np.isfinite(left) & np.isfinite(right)
    sign_change = both_finite & (np.sign(left) * np.sign(right) < 0)
    large_both = np.minimum(np.abs(left), np.abs(right)) > _ASYMPTOTE_FACTOR * max(typical, 1e-12)
    jumps |= sign_change & large_both

    cleaned[1:][jumps] = np.nan
    return cleaned


def build_figure(
    curves: list[Curve],
    markers: list[IntersectionMarker],
    x_range: tuple[float, float],
    y_range: tuple[float, float] | None = None,
    focus_pairs: frozenset[str] | None = None,
    dimmed_names: frozenset[str] = frozenset(),
) -> go.Figure:
    """Dựng biểu đồ 2D gồm các đường cong, điểm giao và chú thích tọa độ.

    Args:
        curves: Các đường cong đã lấy mẫu.
        markers: Các giao điểm cần đánh dấu.
        x_range: Khoảng hiển thị trên trục hoành ``(x_min, x_max)``.
        y_range: Khoảng hiển thị trục tung. Nếu ``None``, khung được tự tính từ dữ liệu.
        focus_pairs: Các cặp cần làm nổi bật. ``None`` nghĩa là không ở chế độ làm nổi bật.
            Khi có giá trị, các đường cong và những cặp khác bị làm mờ.
        dimmed_names: Tên các hàm bị bỏ tích ở thanh legend, ví dụ ``{"f2"}``. Đường của hàm này
            và mọi cặp có liên quan đến hàm đó được làm mờ.

    Returns:
        Biểu đồ Plotly nền tối. Mỗi cặp giao có một màu riêng, và chú thích có màu chữ trùng màu cặp.
    """
    frame_y = y_range if y_range is not None else compute_y_range(curves, markers)
    frame_height = frame_y[1] - frame_y[0]
    focus = focus_pairs is not None

    fig = go.Figure()
    for curve in curves:
        y_values = break_discontinuities(curve.y, frame_height) if curve.cut_jumps else curve.y
        fig.add_trace(
            go.Scatter(
                x=curve.x,
                y=y_values,
                mode="lines",
                name=curve.label,
                line=dict(color=curve.color, width=3),
                opacity=DIM_OPACITY if focus or function_name(curve.label) in dimmed_names else 1.0,
                hovertemplate=f"{curve.label}<br>x=%{{x:.4f}}<br>y=%{{y:.4f}}<extra></extra>",
            )
        )

    for pair in _ordered_pairs(markers):
        group = [m for m in markers if m.pair == pair]
        highlighted = (not focus or pair in focus_pairs) and not (pair_functions(pair) & dimmed_names)
        fig.add_trace(
            go.Scatter(
                x=[m.point.x for m in group],
                y=[m.point.y for m in group],
                mode="markers",
                name=pair,
                marker=dict(
                    size=18 if focus and highlighted else 11,
                    color=pair_color(pair),
                    line=dict(color=BACKGROUND_COLOR, width=2),
                ),
                showlegend=False,
                opacity=1.0 if highlighted else DIM_OPACITY + 0.1,
                hovertemplate=f"{pair}<br>x=%{{x:.4f}}<br>y=%{{y:.4f}}<extra></extra>",
            )
        )

    if markers:
        anchors = _merge_coincident(markers)
        # Việc đặt nhãn tốn thời gian tăng theo bình phương số điểm. Quá nhiều điểm thì không
        # vẽ nhãn nào; mọi điểm vẫn có marker, và tọa độ vẫn có ở phần liệt kê hoặc khi rê chuột.
        if len(anchors) <= MAX_LABELED_POINTS:
            offsets = place_labels([anchor for anchor, _ in anchors], x_range, frame_y)
        else:
            offsets = [None] * len(anchors)
        for (anchor, pairs), offset in zip(anchors, offsets, strict=True):
            # Nhãn bị ẩn khi không có chỗ trống: điểm vẫn có marker và tọa độ trong bảng.
            if offset is None:
                continue
            ax, ay = offset
            highlighted = (not focus or any(pair in focus_pairs for pair in pairs)) and not any(
                pair_functions(pair) & dimmed_names for pair in pairs
            )
            _add_intersection_annotation(fig, anchor, ax, ay, 1.0 if highlighted else 0.3)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", color=TEXT_COLOR),
        height=560,
        margin=dict(l=64, r=20, t=30, b=56),
        showlegend=False,
        hovermode="closest",
        xaxis=_axis_style("x", list(x_range)),
        yaxis=_axis_style("y", list(frame_y)),
    )
    return fig


def _axis_style(title: str, axis_range: list[float]) -> dict[str, object]:
    """Kiểu trục 2D: có đường trục, vạch chia, nhãn số và tên trục, để người dùng thấy cả hai trục."""
    return dict(
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=14)),
        range=axis_range,
        showline=True,
        linecolor=AXIS_LINE_COLOR,
        linewidth=1.5,
        ticks="outside",
        tickcolor=AXIS_LINE_COLOR,
        showticklabels=True,
        tickfont=dict(color=TEXT_COLOR, size=12),
        gridcolor=GRID_COLOR,
        zeroline=True,
        zerolinecolor=AXIS_LINE_COLOR,
        zerolinewidth=1.0,
    )


def place_labels(
    markers: list[IntersectionMarker],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    plot_size: tuple[int, int] = PLOT_SIZE_PX,
) -> list[tuple[int, int] | None]:
    """Chọn vị trí chú thích cho từng giao điểm để các hộp chữ không chồng nhau.

    Thuật toán tham lam: với mỗi giao điểm, thử lần lượt các độ lệch ứng viên quanh điểm
    và chọn vị trí đầu tiên nằm gọn trong vùng vẽ và không chồng lên hộp đã đặt.

    Khi mọi vị trí ứng viên đều chồng, nhãn bị ẩn (``None``) thay vì đè chữ lên nhau. Điểm
    vẫn được đánh dấu trên đồ thị, tọa độ vẫn hiện trong bảng và khi rê chuột. Đây là cách
    đánh đổi khi nhiều giao điểm nằm sát nhau, ví dụ khi khung x rộng và đường dao động dày.

    Args:
        markers: Các giao điểm cần đặt chú thích.
        x_range: Khoảng trục x đang hiển thị, dùng để quy đổi sang pixel.
        y_range: Khoảng trục y đang hiển thị.
        plot_size: Kích thước ước lượng vùng vẽ ``(rộng, cao)`` theo pixel.

    Returns:
        Danh sách, theo thứ tự ``markers``. Mỗi phần tử là cặp ``(ax, ay)`` độ lệch pixel của
        hộp chữ so với điểm, hoặc ``None`` nếu không tìm được chỗ trống nên ẩn nhãn.
    """
    width, height = plot_size
    x0, x1 = x_range
    y0, y1 = y_range
    placed: list[tuple[float, float, float, float]] = []  # (trái, trên, phải, dưới)
    result: list[tuple[int, int] | None] = []

    for marker in markers:
        px = (marker.point.x - x0) / (x1 - x0) * width
        py = (y1 - marker.point.y) / (y1 - y0) * height
        box_w, box_h = _label_box_size(marker)

        chosen: tuple[int, int] | None = None
        for ax, ay in _LABEL_CANDIDATES:
            cx, cy = px + ax, py + ay
            box = (cx - box_w / 2, cy - box_h / 2, cx + box_w / 2, cy + box_h / 2)
            # Chữ bị cắt ở mép vùng vẽ là lỗi hiển thị, nên loại vị trí đó.
            outside = box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height
            if outside or any(_overlap_area(box, other) > 0 for other in placed):
                continue
            chosen = (ax, ay)
            placed.append(box)
            break
        result.append(chosen)
    return result


_BASE_LABEL_OFFSETS: tuple[tuple[int, int], ...] = (
    (50, -50),
    (-50, -50),
    (50, 50),
    (-50, 50),
    (0, -78),
    (0, 78),
    (120, 0),
    (-120, 0),
)
"""Tám hướng quanh điểm, ưu tiên các vị trí gần điểm nhất."""

_LABEL_CANDIDATES: tuple[tuple[int, int], ...] = _BASE_LABEL_OFFSETS + tuple(
    (round(ax * factor), round(ay * factor))
    for factor in (1.6, 2.2)
    for ax, ay in _BASE_LABEL_OFFSETS
)
"""Các độ lệch pixel ứng viên. Gần điểm trước, xa dần khi vùng quanh điểm đã đông chú thích."""

MAX_LABELED_POINTS: int = 200
"""Số điểm giao tối đa được gắn nhãn. Trên mức này nhãn chồng chất đến mức không đọc được."""

_LABEL_CHAR_WIDTH: float = 7.5
_LABEL_LINE_HEIGHT: float = 20.0
_LABEL_PADDING: float = 12.0


def _ordered_pairs(markers: Iterable[IntersectionMarker]) -> list[str]:
    """Các nhãn cặp theo thứ tự xuất hiện lần đầu, không trùng."""
    seen: list[str] = []
    for marker in markers:
        if marker.pair not in seen:
            seen.append(marker.pair)
    return seen


def _merge_coincident(markers: list[IntersectionMarker]) -> list[tuple[IntersectionMarker, list[str]]]:
    """Gộp các giao điểm trùng tọa độ thành một chú thích, liệt kê mọi cặp đi qua điểm đó.

    Nhiều đường có thể cùng đi qua một điểm, ví dụ ``(-3; 0)``. Vẽ một chú thích cho mỗi cặp
    sẽ chồng lên nhau không thể tránh. Gộp lại thì mỗi điểm chỉ có một nhãn.

    Args:
        markers: Các giao điểm, có thể trùng tọa độ.

    Returns:
        Danh sách cặp ``(giao điểm đại diện, các cặp đi qua điểm)``, theo thứ tự xuất hiện.
        Khi một điểm chỉ thuộc một cặp, nhãn đại diện giữ đúng tên cặp và màu của cặp.
    """
    groups: dict[tuple[float, float], list[IntersectionMarker]] = {}
    for marker in markers:
        key = (round(marker.point.x, 6), round(marker.point.y, 6))
        groups.setdefault(key, []).append(marker)

    merged: list[tuple[IntersectionMarker, list[str]]] = []
    for group in groups.values():
        pairs = _ordered_pairs(group)
        label = pairs[0] if len(pairs) == 1 else ", ".join(pairs)
        anchor = IntersectionMarker(pair=label, point=group[0].point)
        merged.append((anchor, pairs))
    return merged


def _label_box_size(marker: IntersectionMarker) -> tuple[float, float]:
    """Ước lượng kích thước pixel của hộp chữ chú thích hai dòng.

    Args:
        marker: Giao điểm có chú thích.

    Returns:
        Cặp ``(rộng, cao)`` theo pixel.
    """
    lines = _marker_text(marker).split("\n")
    longest = max(len(line) for line in lines)
    return longest * _LABEL_CHAR_WIDTH + _LABEL_PADDING, 2 * _LABEL_LINE_HEIGHT + _LABEL_PADDING / 2


def _overlap_area(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    """Diện tích giao của hai hình chữ nhật ``(trái, trên, phải, dưới)``, bằng 0 nếu không giao."""
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    return max(0.0, width) * max(0.0, height)


def _marker_text(marker: IntersectionMarker) -> str:
    """Nội dung chú thích hai dòng: tên cặp và tọa độ ``(x; y)``."""
    point = marker.point
    return f"{marker.pair}\n({point.x:.4f}; {point.y:.4f})"


def _add_intersection_annotation(
    fig: go.Figure,
    marker: IntersectionMarker,
    ax: int,
    ay: int,
    opacity: float,
) -> None:
    """Thêm chú thích tọa độ cho một giao điểm, với màu chữ trùng màu cặp.

    Args:
        fig: Biểu đồ đích, được sửa tại chỗ.
        marker: Giao điểm cần chú thích.
        ax: Độ lệch ngang của hộp chữ so với điểm, theo pixel.
        ay: Độ lệch dọc của hộp chữ so với điểm, theo pixel.
        opacity: Độ mờ của chú thích. Giảm khi cặp không được làm nổi bật.
    """
    point = marker.point
    color = pair_color(marker.pair)
    fig.add_annotation(
        x=point.x,
        y=point.y,
        text=f"<b>{marker.pair}</b><br>({point.x:.4f}; {point.y:.4f})",
        showarrow=True,
        arrowhead=2,
        arrowcolor=color,
        ax=ax,
        ay=ay,
        # Neo giữa để tâm hộp chữ trùng đầu mũi tên, đúng với mô hình đặt nhãn.
        xanchor="center",
        yanchor="middle",
        font=dict(color=color, size=12),
        bgcolor=ANNOTATION_BG,
        bordercolor=color,
        borderwidth=1,
        borderpad=4,
        opacity=opacity,
    )
