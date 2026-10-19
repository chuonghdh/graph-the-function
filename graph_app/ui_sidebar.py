"""Thanh bên: danh sách ô nhập phương trình động (2 đến 6), nút thêm/xóa, và cấu hình phạm vi.

Danh sách ô được giữ trong ``st.session_state`` dưới dạng các mã định danh ổn định. Nhờ vậy khi
người dùng xóa một ô ở giữa, các ô còn lại vẫn giữ đúng nội dung. Không có nút chọn chế độ:
chiều không gian (2D hay 3D) do ``equations.detect_dimension`` quyết định từ mọi ô nhập.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from graph_app.plotting import PALETTE
from graph_app.presets import PRESET_PLACEHOLDER, PRESETS
from graph_app.plotting_3d import COLORSCALES
from graph_app.ui_help import open_cheatsheet_button

MIN_EQUATIONS: int = 2
"""Số ô nhập tối thiểu khi mở ứng dụng và khi xóa. Không cho xóa xuống dưới mức này."""

MAX_EQUATIONS: int = 6
"""Số ô nhập tối đa, theo yêu cầu so sánh đồng thời tối đa sáu hàm số."""

DEFAULT_TEXTS: tuple[str, ...] = ("x^2 - 2", "sin(x)")
"""Nội dung mặc định của hai ô đầu tiên. Các ô thêm sau mặc định rỗng."""


DEFAULT_XY_RANGE: tuple[float, float] = (-6.0, 6.0)
DEFAULT_Z_RANGE: tuple[float, float] = (-10.0, 10.0)
DEFAULT_RESOLUTION: int = 100
MAX_RESOLUTION: int = 200

_SLOT_IDS_KEY: str = "equation_slot_ids"
_PRESET_KEY: str = "preset_choice"
_NEXT_SLOT_KEY: str = "equation_next_slot_id"


@dataclass(frozen=True)
class SidebarState:
    """Toàn bộ đầu vào người dùng đã nhập ở thanh bên.

    Attributes:
        texts: Nội dung các ô nhập, theo thứ tự hiển thị ``f1``, ``f2``, ...
        x_range: Khoảng trục x ``(min, max)``.
        y_range: Khoảng trục y ``(min, max)``.
        z_range: Khoảng trục z ``(min, max)``, dùng trong đồ thị 3D.
        y_auto: ``True`` nếu đồ thị 2D tự co giãn khung y theo hàm và giao điểm.
        x_auto: ``True`` nếu đồ thị 2D tự canh khung x để chứa mọi giao điểm.
        resolution: Độ phân giải lưới của mặt ``z = f(x, y)``.
        colorscales: Bảng màu 3D cho từng ô nhập, cùng số phần tử với ``texts``.
    """

    texts: tuple[str, ...]
    slot_ids: tuple[int, ...]
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    z_range: tuple[float, float]
    y_auto: bool
    x_auto: bool
    resolution: int
    colorscales: tuple[str, ...]


def render_sidebar() -> SidebarState:
    """Hiển thị thanh bên và trả về toàn bộ đầu vào của người dùng.

    Returns:
        ``SidebarState`` phản ánh các widget hiện tại.
    """
    _init_slots()
    with st.sidebar:
        st.markdown("**Nhập phương trình**")
        slot_ids = list(st.session_state[_SLOT_IDS_KEY])
        texts = tuple(
            _render_equation_row(position, slot_id, can_remove=len(slot_ids) > MIN_EQUATIONS)
            for position, slot_id in enumerate(slot_ids)
        )
        st.button(
            "➕ Thêm hàm số",
            key="add_slot",
            on_click=_add_slot,
            disabled=len(slot_ids) >= MAX_EQUATIONS,
            width="stretch",
        )
        open_cheatsheet_button()

        with st.expander("⚙️ Cấu hình phạm vi & màu sắc", expanded=False):
            x_auto = st.checkbox(
                "Tự canh khung x theo giao điểm (2D)",
                value=True,
                key="x_auto",
                help="Bật: khung x được tính sau khi tìm giao điểm, sao cho chứa mọi giao điểm. Tắt: dùng khoảng x ở dưới.",
            )
            x_range = _axis_inputs("Trục x", "x_range", DEFAULT_XY_RANGE, disabled=x_auto)
            y_range = _axis_inputs("Trục y", "y_range", DEFAULT_XY_RANGE)
            z_range = _axis_inputs("Trục z (chỉ dùng cho 3D)", "z_range", DEFAULT_Z_RANGE)
            y_auto = st.checkbox(
                "Tự co giãn khung y (2D)",
                value=True,
                key="y_auto",
                help="Bật: khung y theo hàm và giao điểm. Tắt: dùng đúng khoảng trục y ở trên.",
            )
            resolution = st.slider(
                "Độ phân giải mặt 3D",
                min_value=20,
                max_value=MAX_RESOLUTION,
                value=DEFAULT_RESOLUTION,
                step=10,
                key="resolution",
                help="Số điểm mỗi chiều của mặt z = f(x, y). Mặt ẩn tối đa 60 điểm mỗi chiều.",
            )
            colorscales = tuple(_colorscale_select(position) for position in range(len(slot_ids)))

    return SidebarState(
        texts=texts,
        slot_ids=tuple(slot_ids),
        x_range=x_range,
        y_range=y_range,
        z_range=z_range,
        y_auto=y_auto,
        x_auto=x_auto,
        resolution=int(resolution),
        colorscales=colorscales,
    )


def axis_ranges_valid(state: SidebarState, dimension: str) -> bool:
    """Kiểm tra min nhỏ hơn max trên các trục đang dùng.

    Trục y luôn được dùng. Trục x bỏ qua khi 2D đang tự canh, vì khi đó khung x do giao điểm
    quyết định. Trục z chỉ kiểm tra khi đồ thị là 3D.

    Args:
        state: Đầu vào của thanh bên.
        dimension: ``"2d"`` hoặc ``"3d"``.

    Returns:
        ``True`` nếu các trục đang dùng đều có min < max.
    """
    ranges = [state.y_range]
    if dimension == "3d" or not state.x_auto:
        ranges.append(state.x_range)
    if dimension == "3d":
        ranges.append(state.z_range)
    return all(low < high for low, high in ranges)


def _init_slots() -> None:
    """Khởi tạo danh sách ô nhập lần đầu, với ``MIN_EQUATIONS`` ô."""
    if _SLOT_IDS_KEY not in st.session_state:
        st.session_state[_SLOT_IDS_KEY] = list(range(MIN_EQUATIONS))
        st.session_state[_NEXT_SLOT_KEY] = MIN_EQUATIONS


def _apply_preset(slot_id: int) -> None:
    """Điền công thức của mẫu vừa chọn vào đúng ô nhập của nó. Chạy trước khi script vẽ lại.

    Args:
        slot_id: Mã định danh của ô nhập có dropdown vừa thay đổi.
    """
    choice = st.session_state.get(f"{_PRESET_KEY}_{slot_id}")
    if choice in PRESETS:
        st.session_state[f"eq_{slot_id}"] = PRESETS[choice]


def _add_slot() -> None:
    """Thêm một ô nhập rỗng ở cuối, nếu chưa đạt giới hạn. Chạy trước khi script vẽ lại."""
    slot_ids: list[int] = st.session_state[_SLOT_IDS_KEY]
    if len(slot_ids) < MAX_EQUATIONS:
        slot_ids.append(st.session_state[_NEXT_SLOT_KEY])
        st.session_state[_NEXT_SLOT_KEY] += 1


def _remove_slot(slot_id: int) -> None:
    """Xóa một ô nhập, nếu vẫn còn trên mức tối thiểu.

    Args:
        slot_id: Mã định danh của ô cần xóa.
    """
    slot_ids: list[int] = st.session_state[_SLOT_IDS_KEY]
    if len(slot_ids) > MIN_EQUATIONS and slot_id in slot_ids:
        slot_ids.remove(slot_id)


def _render_equation_row(position: int, slot_id: int, can_remove: bool) -> str:
    """Hiển thị một hàng nhập liệu: nhãn màu, ô nhập, nút mẫu nổi tiếng và nút xóa.

    Thứ tự các cột từ trái sang phải: ô nhập, icon mẫu nổi tiếng, icon xóa.

    Args:
        position: Vị trí hiển thị của ô, từ 0. Quyết định nhãn ``f{position + 1}`` và màu.
        slot_id: Mã định danh ổn định, dùng làm khóa widget.
        can_remove: ``False`` khi đang ở mức tối thiểu, lúc đó nút xóa bị vô hiệu hóa.

    Returns:
        Chuỗi người dùng nhập.
    """
    color = PALETTE[position % len(PALETTE)]
    st.markdown(
        f"<div style='border-left:4px solid {color};padding-left:8px;font-weight:600'>f{position + 1}</div>",
        unsafe_allow_html=True,
    )
    input_col, preset_col, remove_col = st.columns([7, 1, 1], vertical_alignment="center", gap="small")
    with input_col:
        text = st.text_input(
            f"Phương trình f{position + 1}",
            value=DEFAULT_TEXTS[slot_id] if slot_id < len(DEFAULT_TEXTS) else "",
            key=f"eq_{slot_id}",
            placeholder="Ví dụ: x^2 + y^2 = 25  hoặc  z = x*y",
            label_visibility="collapsed",
            help="Nhập y = f(x), z = f(x, y), A = B hoặc một biểu thức (ngầm hiểu = 0).",
        )
    with preset_col:
        with st.popover("", icon=":material/library_books:", help=f"Hàm số nổi tiếng cho f{position + 1}"):
            st.selectbox(
                f"Hàm số nổi tiếng cho f{position + 1}",
                options=[PRESET_PLACEHOLDER, *PRESETS],
                index=0,
                key=f"{_PRESET_KEY}_{slot_id}",
                on_change=_apply_preset,
                args=(slot_id,),
            )
    with remove_col:
        st.button(
            "",
            icon=":material/close:",
            key=f"del_{slot_id}",
            help=f"Xóa f{position + 1}",
            on_click=_remove_slot,
            args=(slot_id,),
            disabled=not can_remove,
        )
    return text


def _axis_inputs(
    label: str,
    key: str,
    default: tuple[float, float],
    disabled: bool = False,
) -> tuple[float, float]:
    """Hai ô nhập số cho đầu min và max của một trục.

    Ô nhập cho phép gõ giá trị chính xác, thay vì chỉ kéo thanh trượt. Nếu min không nhỏ hơn max,
    hàm vẫn trả về giá trị đó; điểm vào ứng dụng sẽ báo lỗi và không vẽ.

    Args:
        label: Nhãn của trục, ví dụ ``"Trục x"``.
        key: Tiền tố khóa widget, phải duy nhất trên trang.
        default: Khoảng mặc định ``(min, max)``.
        disabled: ``True`` để khóa ô nhập, ví dụ khi khung đang được tự canh.

    Returns:
        Cặp ``(min, max)`` dạng float.
    """
    st.markdown(f"**{label}**")
    low_col, high_col = st.columns(2, gap="small")
    with low_col:
        low = st.number_input(
            "min",
            value=float(default[0]),
            step=0.5,
            format="%.2f",
            key=f"{key}_min",
            disabled=disabled,
        )
    with high_col:
        high = st.number_input(
            "max",
            value=float(default[1]),
            disabled=disabled,
            step=0.5,
            format="%.2f",
            key=f"{key}_max",
        )
    return float(low), float(high)


def _colorscale_select(position: int) -> str:
    """Hộp chọn bảng màu 3D cho một ô nhập, theo vị trí hiển thị.

    Args:
        position: Vị trí ô, từ 0.

    Returns:
        Tên bảng màu đã chọn.
    """
    return st.selectbox(
        f"Bảng màu 3D cho f{position + 1}",
        options=COLORSCALES,
        index=position % len(COLORSCALES),
        key=f"cs_{position}",
    )
