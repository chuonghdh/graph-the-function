"""Chủ đề giao diện Dark Mode: nền, chữ, ô nhập, header một dòng và badge trạng thái.

Màu nền và màu chữ chính cũng được khai báo trong ``.streamlit/config.toml``. Module này
bổ sung phần CSS mà config không chỉnh được: thu gọn khoảng trắng trên cùng, canh lề badge,
và chống tràn chữ.
"""

from __future__ import annotations

import streamlit as st

BACKGROUND_COLOR: str = "#0E1117"
"""Nền xám đen cao cấp của toàn ứng dụng."""

SURFACE_COLOR: str = "#161B22"
"""Nền của thanh bên và các ô nhập, sáng hơn nền chính một bậc để tạo chiều sâu."""

ACCENT_COLOR: str = "#00F0FF"
"""Màu nhấn neon cyan, dùng cho badge 2D và viền khi focus."""

MAGENTA_ACCENT: str = "#FF2BD6"
"""Màu nhấn neon magenta, dùng cho badge 3D."""

DARK_CSS: str = f"""
<style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
        color: #E6EDF3;
        font-family: "Inter", "Segoe UI", Roboto, system-ui, sans-serif;
    }}
    /* Chừa khoảng trên đủ lớn để thanh Deploy mặc định của Streamlit không che header. */
    .block-container {{
        padding-top: 3.4rem !important;
        padding-bottom: 0.5rem !important;
    }}
    .app-title {{
        margin: 0;
        padding: 0;
        font-size: 1.35rem;
        font-weight: 700;
        line-height: 2.2rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    [data-testid="stSidebar"] {{
        background-color: {SURFACE_COLOR};
    }}
    /* Ô nhập: font đơn cách để dễ đọc ký tự như dấu * và ^. */
    .stTextInput input {{
        font-family: "Consolas", "Cascadia Mono", monospace;
        background-color: {SURFACE_COLOR};
        border: 1px solid #30363D;
        border-radius: 8px;
    }}
    .stTextInput input:focus {{
        border-color: {ACCENT_COLOR};
        box-shadow: 0 0 0 1px {ACCENT_COLOR};
    }}
    /* Chống tràn chữ: biểu thức dài và thông báo tự xuống dòng thay vì đẩy bố cục. */
    .stMarkdown, .stAlert, [data-testid="stCaptionContainer"] {{
        overflow-wrap: anywhere;
        word-break: break-word;
    }}
    .mode-badge-wrap {{
        text-align: right;
        white-space: nowrap;
    }}
    .mode-badge {{
        display: inline-block;
        max-width: 100%;
        padding: 0.25rem 0.8rem;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .mode-badge-2d {{
        color: {ACCENT_COLOR};
        background-color: rgba(0, 240, 255, 0.12);
        border: 1px solid {ACCENT_COLOR};
    }}
    .mode-badge-3d {{
        color: {MAGENTA_ACCENT};
        background-color: rgba(255, 43, 214, 0.12);
        border: 1px solid {MAGENTA_ACCENT};
    }}
    /* Điện thoại: thu nhỏ lề, tiêu đề và badge xếp gọn. */
    @media (max-width: 640px) {{
        .block-container {{ padding-left: 0.8rem; padding-right: 0.8rem; padding-top: 3.2rem !important; }}
        .app-title {{ font-size: 1.1rem; }}
        /* Vùng vẽ quá hẹp để chứa nhãn chú thích mà không chồng chữ. Tọa độ vẫn có trong danh sách. */
        .js-plotly-plot .annotation {{ display: none !important; }}
    }}
</style>
"""
"""Mã CSS đưa vào trang. Mọi màu đều lấy từ hằng số ở trên để dễ đổi chủ đề."""

_BADGE_LABELS: dict[str, str] = {
    "2d": "Chế độ Đồ thị 2D",
    "3d": "Chế độ Đồ thị 3D",
}


def apply_dark_theme() -> None:
    """Đưa CSS Dark Mode vào trang hiện tại. Gọi một lần ở đầu mỗi lần chạy script."""
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def render_header(dimension: str) -> None:
    """Header một dòng: tiêu đề bên trái, badge trạng thái canh phải.

    Args:
        dimension: ``"2d"`` hoặc ``"3d"``, lấy từ ``equations.detect_dimension``.
    """
    title_col, badge_col = st.columns([5, 4], vertical_alignment="center", gap="small")
    with title_col:
        st.markdown("<div class='app-title'>📈 Vẽ đồ thị hàm số</div>", unsafe_allow_html=True)
    with badge_col:
        label = _BADGE_LABELS.get(dimension, _BADGE_LABELS["2d"])
        st.markdown(
            f"<div class='mode-badge-wrap'><span class='mode-badge mode-badge-{dimension}'>"
            f"🔄 [TỰ ĐỘNG DETECT] {label}</span></div>",
            unsafe_allow_html=True,
        )
