"""Danh mục 20 hàm số kinh điển: 10 đường 2D và 10 mặt 3D, dùng cho dropdown "Hàm số nổi tiếng".

Mỗi mẫu là một chuỗi có thể nhập trực tiếp vào ô phương trình. Chiều (2D hay 3D) không được khai báo
riêng: hệ thống tự nhận diện từ biến ``z`` xuất hiện trong chuỗi, đúng như khi người dùng gõ tay.

Lưu ý về mặt trụ ``x² + y² = 9``: công thức này không chứa ``z``, nên quy tắc tự nhận diện
sẽ xếp nó vào 2D. Để nó được vẽ đúng là mặt trụ trong không gian 3D, mẫu dùng dạng tương đương
``x² + y² = 9 + sin²(z) + cos²(z) − 1``. Vế thêm vào luôn bằng 0 (đồng nhất thức), nên tập nghiệm
vẫn là hình trụ bán kính 3, và chuỗi có chứa ``z``. Bộ phân tích SymPy tự rút gọn các dạng đơn giản
hơn như ``z − z`` hoặc ``0*z`` nên không giữ được ``z``.
"""

from __future__ import annotations

PRESET_PLACEHOLDER: str = "— Chọn một hàm số nổi tiếng —"
"""Mục đầu tiên của dropdown: không làm gì, dùng để đưa dropdown về trạng thái nghỉ."""

PRESETS: dict[str, str] = {
    # ---- Nhóm đường cong 2D ----
    "2D - Lemniscate of Bernoulli (Hình số 8)": "(x**2 + y**2)**2 = 2*(x**2 - y**2)",
    "2D - Folium of Descartes (Lá Descartes)": "x**3 + y**3 - 3*x*y = 0",
    "2D - Witch of Agnesi (Phù thủy Agnesi)": "y*(x**2 + 4) = 8",
    "2D - Cardioid (Đường hình tim)": "(x**2 + y**2 - x)**2 = x**2 + y**2",
    "2D - Damped Sine Wave (Sóng tắt dần)": "y = exp(-0.2*x) * sin(2*x)",
    "2D - Gaussian Curve (Đường chuông Gauss)": "y = exp(-x**2)",
    "2D - Logistic Function (Hàm Logistic)": "y = 1 / (1 + exp(-x))",
    "2D - Catenary (Đường xích đạo)": "y = (exp(x) + exp(-x)) / 2",
    "2D - Cubic Parabola (Parabol bậc 3)": "y = x**3 - 3*x",
    "2D - Sinc Function (Hàm Sinc)": "y = sin(x) / (x + 0.0001)",
    # ---- Nhóm mặt 3D ----
    "3D - Sombrero / Mexican Hat (Mặt Mũ Mexican)": "z = sin(sqrt(x**2 + y**2)) / (sqrt(x**2 + y**2) + 0.001)",
    "3D - Hyperbolic Paraboloid (Mặt Yên ngựa)": "z = x**2 - y**2",
    "3D - Monkey Saddle (Yên ngựa 3 múi)": "z = x**3 - 3*x*y**2",
    "3D - Sphere (Mặt cầu bán kính 5)": "x**2 + y**2 + z**2 = 25",
    "3D - Egg Carton (Mặt vỉ trứng)": "z = sin(x) * cos(y)",
    "3D - Circular Ripple (Sóng nước lan tỏa)": "z = sin(sqrt(x**2 + y**2))",
    "3D - Elliptic Paraboloid (Parabol Elliptic)": "z = x**2 + 2*y**2",
    "3D - Cone (Mặt nón)": "x**2 + y**2 - z**2 = 0",
    "3D - Cylinder (Mặt trụ)": "x**2 + y**2 = 9 + sin(z)**2 + cos(z)**2 - 1",
    "3D - Cosine Wave Grid (Lưới sóng Cosine)": "z = cos(x) + cos(y)",
}
"""20 mẫu theo thứ tự hiển thị: 10 đường 2D trước, 10 mặt 3D sau."""
