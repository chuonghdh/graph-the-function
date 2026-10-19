# 📈 Vẽ đồ thị hàm số 2D và 3D

Ứng dụng web vẽ đồ thị hàm số, cập nhật ngay khi bạn sửa công thức, giao diện Dark Mode. Không có nút chọn chế độ: ứng dụng tự nhận diện 2D hay 3D từ nội dung bạn gõ.

- **Đồ thị 2D:** vẽ `y = f(x)` hoặc phương trình ẩn như `x^2 + y^2 = 25`, tối đa sáu phương trình cùng lúc. Tự tìm và đánh dấu **giao điểm**, kèm tọa độ `(x; y)`.
- **Đồ thị 3D:** mặt `z = f(x, y)` hoặc mặt ẩn `F(x, y, z) = 0` như `x^2 + y^2 + z^2 = 25`, tối đa sáu hàm. Xoay, phóng to, di chuột xem tọa độ. Tự tính **đường giao** giữa các mặt.

Xây dựng bằng **Python**, **Streamlit**, **Plotly**, **SymPy**, **NumPy**, **SciPy** và **contourpy**.

---

## ✨ Tính năng

- **Nhập công thức tự nhiên:** `x^3 - 2x + 1`, `2x + 1`, `sin(x)/x`, `sqrt(x)`, `log(x)`, `|x|`, `e^x`, `pi`.
- **Nhiều phương trình:** bấm ➕ để thêm, ✖ để xóa. Mỗi hàm có một màu riêng.
- **20 hàm số nổi tiếng:** 10 đường 2D và 10 mặt 3D. Bấm biểu tượng 📚 cạnh ô nhập để điền mẫu vào đúng ô đó.
- **Thanh legend trên đồ thị:** bỏ tích một hàm để làm mờ đường hoặc mặt của hàm đó và các giao điểm liên quan.
- **Làm nổi bật giao điểm:** mỗi cặp có checkbox dưới đồ thị. Tích vào để phóng to cặp đó.
- **Khung tự canh:** khung x và y được tính sau khi tìm xong giao điểm, để chứa mọi giao điểm. Có thể tắt và nhập khung tay.
- **Giao điểm chính xác:** đa thức được giải đúng bằng SymPy. Hàm khác được dò đổi dấu rồi giải bằng chia đôi. Tiếp xúc được phát hiện bằng cực tiểu và Levenberg–Marquardt.
- **Đường giao 3D chính xác:** các điểm được chiếu về đúng đường giao bằng Gauss–Newton. Điểm tiếp xúc giữa hai mặt ẩn được đánh dấu riêng.
- **Math Syntax Helper:** bảng cú pháp ở thanh bên và gợi ý sửa lỗi (ví dụ `xy` → `x*y`, `x2` → `x^2`).
- **Xử lý an toàn:** chia cho 0, căn và log ngoài miền xác định được ngắt đường vẽ thay vì gây lỗi. Biểu thức không hợp lệ bị từ chối với thông báo rõ ràng.

---

## 🧮 Cú pháp hàm số

| Nhóm | Ví dụ |
|------|-------|
| Đa thức | `x^2 - 2`, `x**3 + 2*x` |
| Nhân ẩn | `2x + 1`, `3sin(x)` |
| Lượng giác | `sin(x)`, `cos(x)`, `tan(x)`, `asin(x)`, `atan(x)` |
| Hyperbolic | `sinh(x)`, `cosh(x)`, `tanh(x)` |
| Mũ | `exp(x)`, `e^x` |
| Logarit | `log(x)` hoặc `ln(x)` là logarit tự nhiên; `log10(x)`, `log2(x)` |
| Căn, trị tuyệt đối | `sqrt(x)`, `abs(x)`, `|x|` |
| Hằng số | `pi` hoặc `π`, `e` |
| Phương trình ẩn | `x^2 + y^2 = 25`, `x^2/9 + y^2/4 = 1` (2D); `x^2 + y^2 + z^2 = 25` (3D) |

Lưu ý: `log(x)` là logarit tự nhiên. Logarit cơ số 10 dùng `log10(x)`.

Nếu một ô có chứa biến `z`, toàn bộ hệ thống chuyển sang 3D.

---

## 🚀 Chạy ứng dụng cục bộ

Yêu cầu: **Python 3.11 trở lên** (khuyến nghị 3.12).

**Windows (PowerShell):**

```powershell
# 1. Tạo và kích hoạt môi trường ảo
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Cài thư viện
pip install -r requirements-dev.txt

# 3. Chạy ứng dụng
streamlit run app.py
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Mở trình duyệt tại `http://localhost:8501`.

> `requirements.txt` chỉ chứa thư viện runtime. `requirements-dev.txt` thêm `pytest` để chạy test.

### Chạy test

```bash
python -m pytest
```

Bộ test gồm unit test cho lõi toán học, biểu đồ, và đường giao 3D; các ca đặc biệt về giải tích (nghiệm bội, tiệm cận, tiếp xúc, trùng nhau); và smoke test giao diện bằng `streamlit.testing`.

Kiểm thử giao diện tự động (cần Playwright và Chromium):

```bash
python ui_test_agent.py
```

Script này mở trình duyệt headless, chụp ảnh các trạng thái chính vào `ui_artifacts/`, và kiểm tra chồng chữ. Thư mục này không đưa lên Git.

---

## ☁️ Deploy lên Streamlit Community Cloud

Ứng dụng đã sẵn sàng để deploy công khai, không cần chỉnh sửa mã. Mã nguồn đang ở repo GitHub `chuonghdh/graph-the-function`.

1. Vào [share.streamlit.io](https://share.streamlit.io) và đăng nhập bằng GitHub.
2. Chọn **Create app** → **Deploy a public app from GitHub**.
3. Điền thông tin:
   - **Repository:** `chuonghdh/graph-the-function`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Trong **Advanced settings**, chọn **Python 3.12**.
5. Bấm **Deploy**. Sau vài phút, bạn nhận được link công khai dạng `https://<tên-app>.streamlit.app`.

Mỗi lần merge vào `main`, Streamlit Cloud tự build lại.

### Quy trình làm việc

- Phát triển trên nhánh `dev`. Khi xong, mở pull request từ `dev` vào `main` trên GitHub.
- Không commit file `.streamlit/secrets.toml`. File này đã nằm trong `.gitignore`.

---

## 🗂️ Cấu trúc thư mục

```
├── app.py                  # Điểm vào Streamlit: thanh bên, nhận diện 2D/3D
├── graph_app/
│   ├── math_engine.py      # Phân tích biểu thức, giao điểm một biến (đa thức, chia đôi, tiếp xúc)
│   ├── equations.py        # Phân loại phương trình: y = g(x), z = f(x, y), hoặc F = 0
│   ├── implicit.py         # Đường ẩn 2D, giao điểm ẩn 2D (cả giao cắt và tiếp xúc), mặt ẩn 3D
│   ├── refine.py           # Gauss–Newton: chiếu điểm về đường giao, tìm điểm tiếp xúc 3D
│   ├── surface.py          # Lưới, mặt z = f(x, y), đường giao hai mặt tường minh
│   ├── viewport.py         # Miền tính toán, mật độ lấy mẫu, canh khung theo giao điểm
│   ├── presets.py          # 20 hàm số nổi tiếng
│   ├── plotting.py         # Biểu đồ 2D Plotly, đặt nhãn, bảng màu
│   ├── plotting_3d.py      # Biểu đồ 3D Plotly, bảng màu, marker điểm tiếp xúc
│   ├── ui_theme.py         # CSS Dark Mode
│   ├── ui_help.py          # Cheatsheet và hiển thị lỗi
│   ├── ui_sidebar.py       # Ô nhập, mẫu, phạm vi trục, tùy chọn tự canh
│   ├── ui_legend.py        # Thanh legend phía trên đồ thị
│   ├── ui_focus.py         # Checkbox làm nổi bật từng cặp giao
│   ├── ui_2d.py            # Đồ thị 2D
│   └── ui_3d.py            # Cảnh 3D: mặt, mặt ẩn, đường giao
├── tests/                  # Unit test, ca đặc biệt, smoke test giao diện
├── ui_test_agent.py        # Kiểm thử giao diện tự động bằng Playwright
├── docs/
│   ├── SPEC.md             # Đặc tả yêu cầu và tiêu chí chấp nhận
│   └── ARCHITECTURE.md     # Kiến trúc và thuật toán
├── .streamlit/config.toml  # Theme Dark Mode
├── requirements.txt        # Thư viện runtime (dùng cho Streamlit Cloud)
├── requirements-dev.txt    # Thêm pytest và Playwright
├── pytest.ini
├── CLAUDE.md               # Quy chuẩn làm việc và lịch sử quyết định
└── .gitignore
```

Tài liệu chi tiết: [`docs/SPEC.md`](docs/SPEC.md) và [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ⚠️ Giới hạn đã biết

- **Miền số thực:** căn bậc chẵn hoặc lũy thừa phân số của số âm (như `x^(1/3)` với `x < 0`) trả về không xác định.
- **Phạm vi tìm giao điểm:** khi khung tự canh, giao điểm được dò trong `±200`. Giao điểm xa hơn không được tìm.
- **Giao điểm rất dày:** hàm dao động rất nhanh có thể có hàng nghìn giao điểm. Khi vượt ngưỡng, ứng dụng chỉ hiện số lượng và không gắn nhãn từng điểm.
- **Nghiệm kép:** tọa độ tiếp điểm chính xác khoảng `1e-8`, do giới hạn của số thực 64 bit.
- **Đường ẩn 2D rất mảnh:** lưới đường ẩn có bước cỡ `0.3` khi khung rất rộng, nên hình nhỏ có thể bị bỏ sót.
- **Tiếp xúc giữa hai mặt tường minh 3D:** chỉ có đường giao được vẽ. Điểm tiếp xúc chưa được đánh dấu riêng.
- **Nhãn chú thích:** khi quá nhiều giao điểm chồng nhau, nhãn bị ẩn để tránh đè chữ. Tọa độ vẫn có trong bảng và khi rê chuột.
- **Thiết bị hẹp:** dưới 640 px, nhãn chú thích trên đồ thị 2D bị ẩn. Tọa độ vẫn có trong bảng bên dưới.

---

## 📄 Giấy phép

Chưa khai báo. Thêm file `LICENSE` nếu bạn muốn công khai mã nguồn theo một giấy phép cụ thể.
