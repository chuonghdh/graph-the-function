"""Hàng kết quả giao điểm/giao tuyến: checkbox làm nổi bật ngay bên cạnh mỗi cặp.

Mỗi hàng có dạng ``[Checkbox] | f1 ∩ f2 | thông tin``. Checkbox mặc định không tích.
Khi tích, cặp tương ứng được làm nổi bật trên đồ thị và các phần khác mờ đi.

Module dùng chung cho 2D và 3D, nên quy tắc hiển thị giống nhau.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

import streamlit as st

from graph_app.plotting import pair_color

HIGHLIGHT_KEY_PREFIX: str = "highlight::"


@dataclass(frozen=True)
class PairRow:
    """Một hàng kết quả cho một cặp.

    Attributes:
        pair: Nhãn cặp, ví dụ ``"f1 ∩ f2"``.
        text: Thông tin hiển thị sau nhãn: tọa độ giao điểm (2D) hoặc hệ phương trình giao tuyến (3D).
        has_result: ``False`` nếu cặp không có giao, lúc đó checkbox bị vô hiệu hóa.
    """

    pair: str
    text: str
    has_result: bool


def render_pair_rows(rows: list[PairRow]) -> frozenset[str] | None:
    """Hiển thị các hàng kết quả, mỗi hàng có checkbox làm nổi bật.

    Args:
        rows: Các cặp cần hiển thị, theo đúng thứ tự muốn xem.

    Returns:
        Tập các cặp đang được tích. ``None`` nếu không có cặp nào được tích.
    """
    checked: set[str] = set()
    for row in rows:
        checkbox_col, text_col = st.columns([1, 14], vertical_alignment="center", gap="small")
        with checkbox_col:
            is_checked = st.checkbox(
                f"Làm nổi bật {row.pair}",
                key=f"{HIGHLIGHT_KEY_PREFIX}{row.pair}",
                label_visibility="collapsed",
                disabled=not row.has_result,
            )
        with text_col:
            _render_row_text(row)
        if is_checked and row.has_result:
            checked.add(row.pair)
    return frozenset(checked) if checked else None


def system_text(first: str, second: str) -> str:
    """Câu mô tả giao tuyến bằng hệ phương trình của hai phương trình gốc.

    Args:
        first: Nội dung phương trình thứ nhất, ví dụ ``"x^2 + y^2 = 16"``.
        second: Nội dung phương trình thứ hai.

    Returns:
        Câu tiếng Việt theo chuẩn toán học, không có cụm từ về tô sáng.
    """
    return f"Biểu diễn qua phương trình giao tuyến: {first} và {second}."


def _render_row_text(row: PairRow) -> None:
    """Hiển thị nhãn cặp và thông tin, với màu chữ trùng màu cặp trên đồ thị."""
    color = pair_color(row.pair)
    st.markdown(
        f"<div style='color:{color};overflow-wrap:anywhere'>"
        f"<b>{html.escape(row.pair)}</b> | {html.escape(row.text)}</div>",
        unsafe_allow_html=True,
    )
