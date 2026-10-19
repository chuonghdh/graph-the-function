# 📈 Vẽ đồ thị hàm số 2D

Ứng dụng web vẽ đồ thị hàm số, cập nhật theo thời gian thực, giao diện Dark Mode. Không có nút chọn chế độ: ứng dụng tự nhận diện 2D hay 3D từ nội dung bạn gõ.

- **Đồ thị 2D:** vẽ `y = f(x)` hoặc phương trình ẩn như `x^2 + y^2 = 25`, tối đa ba phương trình cùng lúc. Tự động tìm và đánh dấu **điểm giao nhau**, kèm chú thích tọa độ `(x; y)`.
- **Đồ thị 3D:** mặt `z = f(x, y)` (tối đa hai mặt), hoặc mặt ẩn `F(x, y, z) = 0` như mặt cầu `x^2 + y^2 + z^2 = 25` (tối đa ba mặt). Xoay 360 độ, phóng to, di chuột xem tọa độ `(x, y, z)`. Tự động tính và tô sáng **đường giao** giữa hai mặt.

Xây dựng bằng **Python**, **Streamlit**, **Plotly**, **SymPy** và **NumPy**.

---

## ✨ Tính năng

- **Nhập hàm số tự nhiên:** `x^3 - 2x + 1`, `sin(x)/x`, `sqrt(x)`, `log(x)`, `e^x`, `π`.
- **So sánh tối đa 3 hàm:** mỗi hàm một màu riêng (xanh lam, hồng đỏ, vàng).
- **Thời gian thực:** đổi hàm hoặc kéo thanh trượt, đồ thị cập nhật ngay.
- **Math Syntax Helper:** bảng cú pháp ở thanh bên, cùng gợi ý sửa lỗi khi nhập sai (ví dụ `xy` → `x*y`).
- **3D:** khoảng Min–Max cho trục x và y, độ phân giải lưới tùy chỉnh, bảng màu Viridis, Plasma, Turbo hoặc Electric cho từng mặt.
- **Phân tích giao điểm:** tìm mọi điểm cắt và điểm tiếp xúc, đánh dấu và ghi tọa độ. Tự loại bỏ tiệm cận (như `1/x` tại 0).
- **Xử lý an toàn:** chia cho 0, căn và log ngoài miền xác định được ngắt đường vẽ thay vì gây lỗi. Biểu thức độc hại (như `__import__('os')`) bị từ chối.

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
| Căn, trị tuyệt đối | `sqrt(x)`, `abs(x)` |
| Hằng số | `pi` hoặc `π`, `e` |

Lưu ý: `log(x)` là logarit tự nhiên. Nếu cần logarit cơ số 10 (thường gọi là `lg`), dùng `log10(x)`.

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

Bộ test gồm unit test cho lõi toán học và biểu đồ, cùng smoke test giao diện bằng `streamlit.testing`.

---

## ☁️ Deploy lên Streamlit Community Cloud

Ứng dụng đã sẵn sàng để deploy công khai, không cần chỉnh sửa mã.

### Bước 1. Đưa mã lên GitHub

```bash
git init
git add .
git commit -m "Khởi tạo ứng dụng vẽ đồ thị hàm số"
git branch -M main
git remote add origin https://github.com/<tên-tài-khoản>/<tên-repo>.git
git push -u origin main
```

Trước khi push, kiểm tra `.gitignore` đã loại trừ `venv/` và `__pycache__/`. Tuyệt đối không commit file `.streamlit/secrets.toml`.

### Bước 2. Tạo ứng dụng trên Streamlit Cloud

1. Vào [share.streamlit.io](https://share.streamlit.io) và đăng nhập bằng GitHub.
2. Chọn **Create app** → **Deploy a public app from GitHub**.
3. Điền thông tin:
   - **Repository:** `<tên-tài-khoản>/<tên-repo>`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Trong **Advanced settings**, chọn **Python 3.12**.
5. Bấm **Deploy**. Sau vài phút, bạn nhận được link công khai dạng `https://<tên-app>.streamlit.app`.

### Bước 3. Cập nhật sau này

Mỗi lần `git push` lên nhánh `main`, Streamlit Cloud tự động build lại. Không cần thao tác thêm.

---

## 🗂️ Cấu trúc thư mục

```
├── app.py                  # Điểm vào Streamlit: thanh chuyển 2D / 3D
├── graph_app/
│   ├── math_engine.py      # Phân tích biểu thức (1, 2 hoặc 3 biến), lấy mẫu, giao điểm 2D
│   ├── equations.py        # Phân loại phương trình: y = g(x) hoặc F = A − B = 0
│   ├── implicit.py         # Đường ẩn 2D, giao điểm ẩn, mặt ẩn 3D, đường giao 3D
│   ├── plotting.py         # Biểu đồ 2D Plotly theo Dark Mode
│   ├── surface.py          # Lưới, mặt z = f(x, y), đường giao hai mặt
│   ├── plotting_3d.py      # Biểu đồ 3D Plotly, bảng màu
│   ├── ui_theme.py         # CSS Dark Mode
│   ├── ui_help.py          # Math Syntax Helper và hiển thị lỗi
│   ├── ui_sidebar.py       # Ba ô nhập, phạm vi trục, bảng màu
│   ├── ui_2d.py            # Đồ thị 2D
│   └── ui_3d.py            # Cảnh 3D: mặt z = f(x, y), mặt ẩn và đường giao
├── tests/                  # Unit test và smoke test
├── docs/
│   ├── SPEC.md             # Đặc tả yêu cầu và tiêu chí chấp nhận
│   └── ARCHITECTURE.md     # Kiến trúc và thuật toán
├── .streamlit/config.toml  # Theme Dark Mode
├── requirements.txt        # Thư viện runtime (dùng cho Streamlit Cloud)
├── requirements-dev.txt    # Thêm pytest
├── pytest.ini
├── CLAUDE.md               # Quy chuẩn làm việc và viết code
└── .gitignore
```

Tài liệu chi tiết: [`docs/SPEC.md`](docs/SPEC.md) và [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ⚠️ Giới hạn đã biết

- Chỉ xét miền số thực. Căn bậc chẵn hoặc lũy thừa phân số của số âm (như `x^(1/3)` với `x < 0`) trả về không xác định.
- Giao điểm nằm rất gần nhau (trong cùng một khoảng lưới) có thể bị bỏ sót. Hàm dao động rất nhanh có thể cần khoảng `x` hẹp hơn.
- Chưa hỗ trợ hàm tham số, hàm ẩn `F(x, y, z) = 0` và tọa độ cực, trụ, cầu.
- Đường giao 3D được nội suy trên lưới, nên sai số vị trí cỡ bước lưới. Tăng độ phân giải để chính xác hơn.
- Ô nhập được giữ nguyên khi đổi chiều, vì mọi ô đều ở thanh bên và luôn hiển thị.

---

## 📄 Giấy phép

Chưa khai báo. Thêm file `LICENSE` nếu bạn muốn công khai mã nguồn theo một giấy phép cụ thể.
