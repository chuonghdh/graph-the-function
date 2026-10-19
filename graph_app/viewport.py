"""Miền tính toán mở rộng và mật độ lấy mẫu thích nghi theo độ rộng.

Vì Streamlit không nhận sự kiện zoom/pan từ Plotly (xem ``st.plotly_chart``: chỉ có chọn điểm,
hộp và lasso), mã Python không chạy lại khi người dùng zoom trong trình duyệt. Thay vào đó:

- Dữ liệu được tính trên một miền rộng hơn khung nhìn ``PADDING`` lần độ rộng mỗi phía. Khi
  zoom out, các nhánh đồ thị đã có sẵn và không bị đứt.
- Số điểm lấy mẫu tỉ lệ với độ rộng miền (mật độ không đổi), nên khi zoom in vào khoảng nhỏ,
  lưới vẫn mịn. Có giới hạn trên và dưới để chi phí tính toán và dữ liệu gửi lên trình duyệt
  không tăng vô hạn.

Module không phụ thuộc Streamlit.
"""

from __future__ import annotations

PADDING: float = 1.0
"""Phần mở rộng mỗi phía, tính theo độ rộng khung nhìn. ``1.0`` nghĩa là miền tính rộng gấp ba khung nhìn."""


def domain_for(view: tuple[float, float]) -> tuple[float, float]:
    """Miền tính toán mở rộng bao quanh khung nhìn.

    Args:
        view: Khoảng khung nhìn ``(min, max)``, với min < max.

    Returns:
        Khoảng ``(min, max)`` rộng hơn khung nhìn ``PADDING`` lần độ rộng mỗi phía.
    """
    low, high = view
    pad = PADDING * (high - low)
    return low - pad, high + pad


FIT_MARGIN: float = 0.1
"""Phần đệm mỗi phía khi canh khung theo giao điểm, tính theo độ rộng của bao giao điểm."""

FIT_MIN_SPAN: float = 12.0
"""Độ rộng tối thiểu của khung canh theo giao điểm, để một hoặc vài điểm sát nhau vẫn có bối cảnh."""


def fit_view(xs: list[float], fallback: tuple[float, float]) -> tuple[float, float]:
    """Khoảng x nhỏ nhất (có đệm) chứa mọi hoành độ giao điểm.

    Khung được canh sau khi đã có giao điểm, nên không phụ thuộc khung người dùng nhập.
    Không có giao điểm thì dùng ``fallback``.

    Args:
        xs: Hoành độ các giao điểm cần chứa.
        fallback: Khoảng trả về khi không có điểm nào.

    Returns:
        Khoảng ``(min, max)`` bao trọn mọi ``x`` trong ``xs``, rộng ít nhất ``FIT_MIN_SPAN``.
    """
    if not xs:
        return fallback
    low, high = min(xs), max(xs)
    # Nửa độ rộng lấy max của bao có đệm và nửa FIT_MIN_SPAN, nên luôn chứa cả hai đầu mút.
    half = max((high - low) * (1.0 + 2.0 * FIT_MARGIN) / 2.0, FIT_MIN_SPAN / 2.0)
    center = (low + high) / 2.0
    return center - half, center + half


def samples_for(span: float, density: float, minimum: int, maximum: int) -> int:
    """Số điểm lấy mẫu cho một khoảng, giữ mật độ gần như không đổi khi zoom.

    Args:
        span: Độ rộng của miền tính toán (không phải của khung nhìn).
        density: Số điểm trên mỗi đơn vị độ rộng.
        minimum: Giới hạn dưới, để khung hẹp vẫn đủ mịn.
        maximum: Giới hạn trên, để chi phí tính toán không tăng vô hạn khi zoom out.

    Returns:
        Số điểm nguyên trong khoảng ``[minimum, maximum]``.
    """
    return int(min(max(round(span * density), minimum), maximum))
