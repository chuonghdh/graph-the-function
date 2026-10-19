"""Điểm vào Streamlit: nhận phương trình, tự nhận diện không gian 2D hoặc 3D, rồi vẽ.

Chạy cục bộ: ``streamlit run app.py``

Không có nút chọn chế độ. Mọi quyết định 2D hay 3D được đưa ra từ nội dung các ô nhập
(xem ``graph_app.equations.detect_dimension``). Header một dòng gồm tiêu đề và badge trạng thái.

Mỗi lần người dùng đổi một ô nhập hoặc thanh trượt, Streamlit chạy lại toàn bộ script.
Vì vậy mọi hàm phải nhanh và không giữ trạng thái ngoài session.
"""

from __future__ import annotations

import streamlit as st

from graph_app.equations import detect_dimension, parse_all_equations
from graph_app.ui_2d import render_2d
from graph_app.ui_3d import render_3d
from graph_app.ui_help import show_error
from graph_app.ui_legend import render_legend_bar
from graph_app.ui_sidebar import axis_ranges_valid, render_sidebar
from graph_app.ui_theme import apply_dark_theme, render_header


def main() -> None:
    """Dựng trang: header một dòng, thanh bên nhập liệu, và đồ thị theo chiều đã nhận diện."""
    st.set_page_config(page_title="Vẽ đồ thị hàm số", page_icon="📈", layout="wide")
    apply_dark_theme()

    state = render_sidebar()
    equations, errors = parse_all_equations(state.texts)
    dimension = detect_dimension(equations, state.texts)

    render_header(dimension)
    for message in errors:
        show_error(message)
    if not axis_ranges_valid(state, dimension):
        show_error("Ở mục ⚙️ Cấu hình phạm vi & màu sắc, cận min phải nhỏ hơn cận max trên mọi trục.")
        return

    dimmed = render_legend_bar(equations, state.slot_ids)
    if dimension == "3d":
        render_3d(equations, state, dimmed)
    else:
        render_2d(equations, state, dimmed)


if __name__ == "__main__":
    main()
