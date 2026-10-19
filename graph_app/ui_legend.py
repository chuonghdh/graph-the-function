"""Thanh legend ngang phía trên biểu đồ: bật/tắt từng hàm số bằng checkbox có màu riêng.

Mọi checkbox mặc định được tích. Khi bỏ tích một hàm, đường hoặc mặt của hàm đó và các cặp giao
liên quan được làm mờ, để người dùng tập trung quan sát phần còn lại.

Trạng thái của checkbox gắn với mã định danh ổn định của ô nhập (``slot_id``), nên khi xóa một hàm,
các checkbox khác vẫn giữ nguyên trạng thái.
"""

from __future__ import annotations

import streamlit as st

from graph_app.equations import UserEquation
from graph_app.plotting import PALETTE


def render_legend_bar(equations: dict[int, UserEquation], slot_ids: tuple[int, ...]) -> frozenset[str]:
    """Hiển thị thanh legend và trả về tên các hàm đang bị bỏ tích.

    Args:
        equations: Phương trình đã phân tích, theo vị trí ô.
        slot_ids: Mã định danh ổn định của từng ô, theo thứ tự vị trí.

    Returns:
        Tập tên hàm bị bỏ tích, ví dụ ``frozenset({"f2"})``. Rỗng nếu mọi hàm đều được tích.
    """
    if not equations:
        return frozenset()

    items = sorted(equations.items())
    columns = st.columns(len(items), gap="small", vertical_alignment="top")
    dimmed: set[str] = set()
    styles: list[str] = []
    for column, (position, equation) in zip(columns, items, strict=True):
        slot_id = slot_ids[position]
        name = f"f{position + 1}"
        color = PALETTE[position % len(PALETTE)]
        box_key = f"legend_box_{slot_id}"
        styles.append(f".st-key-{box_key} label p {{ color: {color} !important; font-weight: 600; }}")
        styles.append(f".st-key-{box_key} {{ border-top: 3px solid {color}; padding-top: 0.3rem; }}")
        with column:
            with st.container(key=box_key):
                shown = st.checkbox(
                    f"{name}: {equation.text}",
                    value=True,
                    key=f"legend_{slot_id}",
                    help="Bỏ tích để làm mờ hàm này và các cặp giao liên quan.",
                )
        if not shown:
            dimmed.add(name)

    st.markdown(f"<style>{''.join(styles)}</style>", unsafe_allow_html=True)
    return frozenset(dimmed)
