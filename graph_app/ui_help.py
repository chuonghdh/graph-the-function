"""Thành phần trợ giúp: hộp thoại cú pháp và hiển thị lỗi thân thiện.

Module chỉ chứa lớp giao diện.
"""

from __future__ import annotations

import streamlit as st

_CHEATSHEET = """
**Phép toán**

- Nhân: `*`, ví dụ `2*x`, `x*y`. Nhân ẩn `2x` cũng được.
- Lũy thừa: `^` hoặc `**`, ví dụ `x^2` hoặc `x**2`.
- Căn: `sqrt(x)`. Phân số: `(x+1)/(x-2)`.
- Trị tuyệt đối: `|x|` hoặc `abs(x)`, ví dụ `|x - 1|`.
- Hằng số: `pi` (hoặc `π`) và `e`, ví dụ `sin(pi*x)`, `e**(-x**2)`.

**Loại phương trình (tự nhận diện)**

- `y = x^2 + 2x + 1` hoặc chỉ `sin(x)`: đồ thị 2D.
- `x^2 + y^2 = 25`, `sin(x) = cos(y)`: đường cong 2D.
- `z = x^2 + y^2`: mặt 3D.
- `x^2 + y^2 + z^2 = 16`: mặt ẩn 3D.
- `x^2 + y^2 - 25`: không có dấu `=`, ngầm hiểu `= 0`.

**Hàm và hằng số**

- `sin cos tan asin acos atan sinh cosh tanh`
- `exp`, `log` hoặc `ln` (tự nhiên), `log10`, `log2`, `abs`
- `pi` (hoặc `π`), `e`

**Lỗi thường gặp**

- `x2` → viết `x^2`.
- `xy` → viết `x*y`.
- `2(x+1)` → viết `2*(x+1)`.
- `x <= 2` → bất đẳng thức chưa hỗ trợ, hãy dùng dấu `=`.
"""


@st.dialog("📖 Hướng dẫn cú pháp")
def _cheatsheet_dialog() -> None:
    """Hộp thoại chứa cheatsheet đầy đủ."""
    st.markdown(_CHEATSHEET)


def open_cheatsheet_button() -> None:
    """Nút mở hộp thoại hướng dẫn cú pháp, đặt ngay dưới ô nhập ở thanh bên."""
    if st.button("📖 Hướng dẫn cú pháp", width="stretch", key="open_cheatsheet"):
        _cheatsheet_dialog()


def show_error(message: str) -> None:
    """Hiển thị lỗi nhập liệu bằng khung cảnh báo, với biểu tượng dễ nhận biết.

    Args:
        message: Nội dung lỗi, có thể chứa định dạng Markdown.
    """
    st.error(message, icon="⚠️")
