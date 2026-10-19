# Kiến trúc hệ thống (ARCHITECTURE)

Tác giả vai trò: Researcher & System Architect.
Căn cứ: `docs/SPEC.md` phiên bản 1.0.

---

## 1. Lựa chọn thư viện

| Thư viện | Phiên bản ghim | Vai trò | Lý do chọn |
|----------|----------------|---------|------------|
| Streamlit | 1.66.0 | Giao diện web, vòng lặp tương tác | Viết UI bằng Python thuần, Streamlit Cloud hỗ trợ native, tự chạy lại script khi widget đổi nên đáp ứng yêu cầu thời gian thực. |
| Plotly | 7.1.0 | Vẽ đồ thị tương tác | Có hover, zoom, pan sẵn; template `plotly_dark` có sẵn cho Dark Mode; chú thích (annotation) có tọa độ chính xác. |
| SymPy | 1.14.0 | Phân tích biểu thức chuỗi | Parse được cú pháp toán học tự nhiên (`2x`, `x^2`), hỗ trợ danh sách hàm được phép, biên dịch sang NumPy qua `lambdify`. |
| NumPy | 2.5.4 | Tính toán vector hóa | Tính hàng nghìn điểm cùng lúc, thể hiện NaN cho điểm không xác định. Là nền của Plotly và SymPy. |
| pytest | 9.1.1 | Unit test (chỉ dev) | Chuẩn của Python, hỗ trợ tham số hóa. |

**Đã cân nhắc và loại bỏ:**
- `scipy.optimize` để tìm nghiệm: thêm một phụ thuộc nặng, trong khi bài toán chỉ cần tìm cực tiểu tam phân trên các khoảng nhỏ. Tự cài bằng NumPy gọn hơn.
- `eval()` trực tiếp: không an toàn khi người dùng nhập tùy ý trên web công khai.
- Matplotlib: vẽ tĩnh, không có tương tác hover và chú thích động như Plotly.

---

## 2. Kiến trúc mô-đun

```
            ┌──────────────────────┐
            │       app.py         │  Lớp giao diện (Streamlit)
            │  - widget, bố cục    │  Không chứa logic toán học.
            │  - ghép luồng xử lý  │
            └──────────┬───────────┘
                       │ gọi
          ┌────────────┴────────────┐
          ▼                         ▼
┌─────────────────────┐   ┌─────────────────────────┐
│ graph_app/plotting  │   │ graph_app/math_engine   │  Lớp nghiệp vụ toán học
│ - PALETTE, Dark     │   │ - parse_expression      │  Không import Streamlit.
│ - build_figure      │──▶│ - sample_function       │
│ - compute_y_range   │   │ - find_intersections    │
│ - break_discontin.  │   │ - ParsedFunction        │
└─────────────────────┘   └─────────────────────────┘
```

**Quy tắc phụ thuộc:** giao diện (`app.py`, `ui_*.py`) gọi lõi (`graph_app/*.py` không import Streamlit). Không có chiều ngược. Nhờ vậy mọi lõi kiểm thử được mà không cần khởi động Streamlit.

### 2.1 Danh sách module hiện tại (phiên bản 2.8)

| Module | Vai trò | Phụ thuộc chính |
|---|---|---|
| `math_engine.py` | Phân tích biểu thức an toàn, lấy mẫu, giao điểm một biến | sympy, numpy, scipy |
| `equations.py` | Phân loại `y = g(x)`, `z = f(x, y)`, hoặc `F = A − B = 0` | math_engine |
| `implicit.py` | Đường ẩn 2D, giao điểm ẩn 2D (giao cắt và tiếp xúc), lưới và mặt ẩn 3D | math_engine, refine, contourpy |
| `refine.py` | Gauss–Newton: chiếu điểm về tập nghiệm, tìm điểm tiếp xúc 3D | math_engine |
| `surface.py` | Lưới, mặt `z = f(x, y)`, đường giao hai mặt tường minh | math_engine, refine, contourpy |
| `viewport.py` | Miền tính toán, mật độ lấy mẫu, canh khung theo giao điểm | (thuần Python) |
| `presets.py` | 20 hàm số nổi tiếng | (dữ liệu) |
| `plotting.py` | Biểu đồ 2D, đặt nhãn, khung y, cắt gián đoạn, bảng màu | math_engine |
| `plotting_3d.py` | Biểu đồ 3D, bảng màu, marker điểm tiếp xúc | plotting, surface |
| `ui_theme.py`, `ui_help.py` | CSS Dark Mode, cheatsheet, hiển thị lỗi | streamlit |
| `ui_sidebar.py` | Ô nhập động, mẫu, phạm vi trục, tùy chọn tự canh | streamlit, presets |
| `ui_legend.py`, `ui_focus.py` | Thanh legend, checkbox làm nổi bật từng cặp | streamlit |
| `ui_2d.py`, `ui_3d.py` | Vẽ đồ thị 2D và cảnh 3D, gọi lõi theo đúng thứ tự | streamlit, toàn bộ lõi |
| `app.py` | Điểm vào, nhận diện 2D/3D, kiểm tra miền | ui_* |

---

## 3. Luồng dữ liệu một lần vẽ

```
4 ô nhập (f1, f2, f3, thanh trượt x)
  │
  ▼
parse_expression(text)          ← kiểm tra ký tự, tên, cú pháp; lỗi → ExpressionError
  │                               → st.error hiển thị dưới ô tương ứng
  ▼
ParsedFunction (gọi được như hàm NumPy)
  │
  ├─▶ sample_function(f, x_min, x_max, 1500)  → Curve(label, color, x, y)
  │
  └─▶ find_intersections(fi, fj, x_min, x_max) cho mọi cặp   → IntersectionMarker
          │
          ▼
build_figure(curves, markers, x_range)
  │  ├─ compute_y_range: khung tung độ dựa trên phân vị 2–98%
  │  ├─ break_discontinuities: cắt đường tại tiệm cận
  │  └─ annotation (x; y) cho từng giao điểm
  ▼
st.plotly_chart + st.dataframe (bảng giao điểm)
```

---

## 4. Thuật toán chính

### 4.1 Phân tích biểu thức an toàn

Chuỗi đi qua ba lớp bảo vệ trước khi được biên dịch:

1. **Lọc ký tự.** Chỉ cho phép chữ, số, khoảng trắng và `+ - * / ^ ( ) .`. Chặn `_`, `,`, `!`, `[`, `"`, v.v.
2. **Lọc tên.** Mọi từ định danh phải nằm trong `_ALLOWED_NAMES`. Nhờ đó không thể gọi `__import__`, truy cập thuộc tính `x.real`, hay dùng tên SymPy nội bộ như `Add`.
3. **Namespace hạn chế.** `global_dict` không có `__builtins__`. SymPy vẫn cần namespace nội bộ để dựng cây biểu thức, nên ta cung cấp đúng tập tên của SymPy, không có builtin Python.

Sau khi parse với `evaluate=False`, mọi số nguyên được đổi thành số thực. Lý do: nếu giữ số nguyên, Python sẽ tính trước các lũy thừa như `10**(10**10)` và treo tiến trình.

### 4.2 Lấy mẫu và xử lý miền xác định

- `numpy.errstate(all="ignore")` bọc lời gọi hàm. Chia 0, `log(âm)`, `sqrt(âm)` sinh NaN mà không sinh cảnh báo.
- Giá trị phức (do căn số âm trong một số đường dẫn của SymPy) chỉ giữ phần thực khi phần ảo đủ nhỏ, còn lại thành NaN.
- Mọi `±inf` được đổi thành NaN để Plotly ngắt đường.

### 4.3 Tìm giao điểm một biến (giải phương trình)

Bài toán: tìm `x` sao cho `h(x) = f(x) − g(x) = 0` trên `[x_min, x_max]`. Việc tìm nghiệm tách khỏi việc vẽ, nên không dựa vào các điểm vẽ.

1. **Đa thức (nhánh giải đúng).** Nếu `h` là đa thức theo `x`, dùng `Poly.nroots` của SymPy với 30 chữ số. Hệ số nguyên được đổi về `Integer` trước khi nhận diện, vì parser đổi chúng thành `Float`. Nghiệm bội được giữ.
2. **Đổi dấu.** Với hàm khác, lưới `samples` điểm (tối đa 100 000 khi dò ±200). Mỗi đoạn có `h` đổi dấu được chia đôi đồng loạt trên NumPy (60 vòng). Đoạn chứa điểm NaN bị bỏ, ví dụ tiệm cận của `1/x`.
3. **Cặp nghiệm trong một ô lưới.** Hai đầu ô cùng dấu nhưng đỉnh ngược dấu: đỉnh được ước lượng bằng parabol qua ba điểm lưới rồi kiểm tra dấu thật.
4. **Tiếp xúc.** Cực tiểu địa phương của `|h|` không đổi dấu được tối ưu hóa bằng `minimize_scalar`. Cực trị của chính `h` được dùng khi `|h|` hội tụ sang nghiệm bên cạnh.
5. **Mép miền.** Nghiệm ở mép miền xác định (như `√x = x/2` tại 0) được tìm bằng chia đôi trên tính hữu hạn, với ngưỡng riêng `1e-6`.
6. **Xác nhận.** Mọi ứng viên phải thỏa `|h(x*)| ≤ 1e-9 · max(1, |f(x*)|, |g(x*)|)`. Bước này loại tiệm cận.
7. **Gộp và trùng hàm.** Các nghiệm cách nhau dưới `1e-9` độ rộng miền được gộp. Đoạn trùng nhau (`h = 0` liên tục) không được liệt kê từng điểm. Hai hàm trùng hoàn toàn trả về rỗng.

**Giới hạn:** nghiệm bội chính xác khoảng `1e-8` (căn bậc hai của epsilon float64). Hai nghiệm cách nhau dưới bước lưới được bắt bằng bước 3, nhưng không có đảm bảo tổng quát cho mọi hàm dao động.

### 4.4 Khung tung độ và cắt gián đoạn

- Khung `y` dùng phân vị 2% và 98% của mọi giá trị hữu hạn, thay vì min/max. Nhờ vậy `tan(x)` không ép đồ thị còn lại thu nhỏ.
- Khung luôn bao gồm tung độ các giao điểm, và được đệm 10%.
- Hai mẫu liền kề cách nhau quá `2 × chiều cao khung` được coi là tiệm cận. Điểm sau được đặt thành NaN.

---

## 5. Trạng thái và hiệu năng

- **Không lưu trạng thái phía server.** Mọi kết quả được tính lại mỗi lần chạy script.
- **Số đo phiên bản 2.8** (máy phát triển, Windows): một cặp dao động dày `sin(100x)` với `cos(x)` trên `±200` mất khoảng 0.3 s và cho đúng 12733 nghiệm. Sáu hàm với 15 cặp chạy trong AppTest khoảng 1.4 s. Cặp đường ẩn với hàm tường minh trên khung ±200 mất khoảng 0.2–0.8 s mỗi cặp.
- Không dùng `st.cache_data` vì `ParsedFunction` chứa hàm đã biên dịch, không tuần tự hóa được ổn định. Chi phí tính đã đủ thấp để không cần cache.
- Giới hạn độ dài biểu thức 200 ký tự và số mẫu cố định chặn các trường hợp tốn tài nguyên.

---

## 6. Triển khai

- Điểm vào: `app.py` ở thư mục gốc, đúng yêu cầu của Streamlit Community Cloud.
- Phụ thuộc: `requirements.txt` chỉ chứa thư viện runtime, phiên bản ghim cố định.
- Theme: `.streamlit/config.toml`, được Streamlit Cloud đọc tự động.
- Python: 3.11 trở lên, khuyến nghị 3.12. Trên Streamlit Cloud chọn phiên bản Python trong phần Advanced settings nếu cần.
- Không có secret nào. Nếu sau này cần khóa API, đặt trong Secrets của Streamlit Cloud, không commit vào Git.

---

## 7. Hướng mở rộng (không thuộc phiên bản 1.0)

- Thêm `x_scale` và `y_scale` (log) để vẽ các hàm mũ lớn tốt hơn.
- Hỗ trợ căn bậc lẻ của số âm (`x^(1/3)`) bằng cách đổi dấu tường minh.
- Tách `math_engine` thành gói riêng để tái sử dụng ngoài Streamlit.

---

## 8. Nâng cấp 3D (phiên bản 1.1)

### 8.1 Bố cục module

```
app.py (nhận diện tự động, không còn radio) ──┬──▶ graph_app/ui_2d.py ──▶ math_engine, plotting
                              └──▶ graph_app/ui_3d.py ──▶ math_engine, surface, plotting_3d
```

Chế độ 2D và 3D chỉ chia sẻ `math_engine` (parser dùng chung) và hằng số giao diện trong `plotting`. Không có trạng thái chung giữa hai chế độ.

### 8.2 Thư viện bổ sung

| Thư viện | Phiên bản | Lý do |
|----------|-----------|-------|
| contourpy | 1.4.0 | Trích xuất đường mức (đường giao) có thứ tự từ lưới. Chỉ phụ thuộc NumPy, nhẹ. Đã cân nhắc `skimage.measure.find_contours` nhưng kéo theo SciPy và nhiều phụ thuộc hơn. |

### 8.3 Lưới và mặt Z

- `np.meshgrid(xs, ys)` tạo hai ma trận tọa độ. Parser nhận hai biến và được broadcast trên lưới, nên không cần vòng lặp Python.
- Ma trận `Z` có hình dạng `(ny, nx)`, đúng quy ước `go.Surface`.
- Độ phân giải mặc định 100×100, tối đa 200×200. Ở 200×200 là 40 nghìn đỉnh, vẫn xoay mượt trên máy thông thường.

### 8.4 Đường giao của hai mặt

Đường giao là tập `{(x, y): f₁(x,y) − f₂(x,y) = 0}`, được chiếu lên mặt phẳng xy:

1. Tính `H = Z₁ − Z₂` trên lưới.
2. `contourpy.contour_generator(xs, ys, H).lines(0.0)` trả về các đường mức đã được sắp thứ tự.
3. Với mỗi điểm `(x, y)` trên đường, tính lại `z = f₁(x, y)` để đường nằm đúng trên mặt thứ nhất, không phụ thuộc độ phân giải lưới.
4. Trường hợp suy biến: `H` bằng 0 ở mọi đỉnh (hai mặt trùng nhau) trả về rỗng. Hai mặt song song không có đường mức 0 nên cũng trả về rỗng.

Từ phiên bản 2.8, bước 3 được tinh chỉnh: mỗi điểm được chiếu về `f₁ − f₂ = 0` bằng Gauss–Newton (`refine.project_points`), rồi z = f₁(x, y). Sai số đo được khoảng `1e-16`, không còn phụ thuộc bước lưới.

### 8.5 Khung z

Khung z dùng phân vị 1–99% thay vì min/max, giống khung y của 2D, để đỉnh nhọn như `1/(x²+y²)` không làm mặt còn lại bị thu nhỏ.

### 8.6 Điểm không xác định

Chia 0, căn số âm, log của số không dương trả về `NaN`. Plotly không vẽ đỉnh `NaN`, nên mặt có lỗ đúng vị trí. UI ghi chú số điểm đã ẩn cho từng mặt.

---

## 9. Phương trình ẩn và UI/UX (phiên bản 1.2)

### 9.1 Luồng phương trình

```
ô nhập ──▶ equations.parse_equation_2d / _3d
              ├─ "y = g(x)"            → Equation(explicit, g)          → sample_function → Curve
              └─ "A = B" / biểu thức   → Equation(implicit, F = A − B)
                                              ├─ 2D: implicit_curve_polylines (contourpy, mức 0)
                                              │      implicit_form_2d: explicit g → F = y − g(x)
                                              └─ 3D: isosurface_grid → go.Isosurface
```

### 9.2 Giao điểm và đường giao

| Trường hợp | Thuật toán | Lý do |
|---|---|---|
| 2D: hai `y = f(x)` | Đa thức giải đúng; còn lại: đổi dấu + chia đôi, cặp trong ô, tiếp xúc (mục 4.3) | Chính xác, bắt được nghiệm bội và tiếp xúc |
| 2D: có đường ẩn, giao cắt | Ô lưới có cả F và G đổi dấu → nghiệm tuyến tính → Newton trên `F = G = 0` (`implicit`) | Không cần chia theo x; xử lý được đường cong bất kỳ |
| 2D: có đường ẩn, tiếp xúc | Cực tiểu của `F² + G²` (chuẩn hóa) → Levenberg–Marquardt (`implicit._tangent_solutions`) | Tại tiếp xúc, Jacobian suy biến nên nhánh giao cắt không hội tụ |
| 3D: hai mặt ẩn | Voxel có cả F và G đổi dấu → giao hai mặt phẳng xấp xỉ → cắt theo biên voxel → chiếu đầu mút về `{F = G = 0}` | Vectơ hóa bằng NumPy; đầu mút chính xác đến `1e-16` |
| 3D: điểm tiếp xúc hai mặt ẩn | Cực tiểu 3D của `F² + G²` → Gauss–Newton (`refine.isolated_tangencies`) | Điểm nghiệm kép, chính xác đến `1e-8` |
| 3D: hai mặt tường minh | Đường mức `f₁ − f₂ = 0` (contourpy) → chiếu về đường thật → nâng z = f₁ | Đường giao khớp cả hai mặt đến `1e-16` |

Trường hợp trùng nhau hoàn toàn được nhận diện bằng `|F − G|` xấp xỉ 0 trên toàn lưới, và trả về rỗng.

### 9.3 Đặt nhãn chống chồng chữ

`plotting.place_labels` chạy tham lam. Mỗi chú thích thử 12 độ lệch ứng viên quanh điểm, chọn vị trí đầu tiên không giao với hộp đã đặt. Kích thước hộp ước lượng theo số ký tự và vùng vẽ 900×620 px, khớp layout. Nếu mọi vị trí đều chồng, chọn vị trí có diện tích chồng nhỏ nhất.

Hạn chế: ước lượng pixel không đo được độ rộng font thật, nên trên màn hình rất hẹp có thể còn chồng nhẹ.

### 9.4 Chi phí tính toán

Đo cục bộ: ba phương trình ẩn 2D (lưới 300×300) cùng các cặp giao điểm mất khoảng 43 ms. Mặt ẩn 3D lưới 60³ với một cặp mặt mất khoảng 29 ms. Lưới 3D lớn hơn 60 bị giới hạn vì dữ liệu gửi lên trình duyệt tăng theo lập phương.

### 9.5 Chủ đề giao diện

Màu nền và chữ cơ bản khai báo trong `.streamlit/config.toml`. `ui_theme.apply_dark_theme` bổ sung CSS cho ô nhập, thanh chuyển chế độ và thanh bên, mọi màu đều lấy từ hằng số để đổi chủ đề một chỗ.

---

## 10. Tự động nhận diện (phiên bản 1.3)

### 10.1 Luồng

```
thanh bên: 3 ô nhập ──▶ equations.parse_all_equations  (mỗi ô → UserEquation hoặc lỗi theo tên ô)
                    ├──▶ equations.detect_dimension     ("3d" nếu có z ở bất kỳ ô nào, kể cả ô lỗi)
                    ▼
            app.py: badge + lỗi ──▶ ui_2d.render_2d   (dimension = "2d")
                                └─▶ ui_3d.render_3d   (dimension = "3d")
```

### 10.2 Phân tích một ô nhập

`parse_user_equation` làm việc trên biểu thức SymPy, với tập biến cho phép là `x`, `y`, `z`. Các biến thật sự xuất hiện được lấy từ `expr.free_symbols`. Thứ tự xét:

1. Không có `=`: chứa `y` hoặc `z` thì là `implicit` (`expr = 0`), còn lại là `explicit_y` (`y = expr`).
2. Có `=`, vế trái là `y` và vế phải chỉ có `x`: `explicit_y`.
3. Có `=`, vế trái là `z` và vế phải chỉ có `x`, `y`: `explicit_z`.
4. Các trường hợp khác: `implicit` với `F = A − B`.

Chiều của một phương trình là `3d` nếu biểu thức chứa `z`. Mỗi `UserEquation` lưu sẵn các dạng biên dịch cần dùng: `func` (để vẽ trực tiếp), `implicit_2d` (không có nếu chứa `z`), và `implicit_3d` (luôn có, để dựng isosurface và đường giao).

### 10.3 Vì sao `y = g(x)` trong 3D là mặt trụ

Trong không gian ba chiều, tập `{y = g(x)}` không phụ thuộc `z` nên là một mặt trụ đứng. Dạng `F(x, y, z) = y − g(x)` cho đúng hình đó khi dựng isosurface. Điều này giữ nhất quán với cách nhập ở 2D.

### 10.4 Cảnh 3D chung

`plotting_3d.build_scene_3d` nhận một danh sách mặt tường minh (`go.Surface`), một danh sách mặt ẩn (`go.Isosurface`) và một danh sách đường giao. Các đường giao được gộp thành một trace `Scatter3d` bằng hàng `NaN` ngăn cách, nên số trace không tăng theo số đường.

Lưới được tách thành hai mật độ:

- Mặt tường minh dùng độ phân giải người dùng chọn, tối đa 200.
- Mặt ẩn và đường giao dùng `min(độ phân giải, 60)`, vì dữ liệu isosurface tăng theo lập phương.

### 10.5 Đường giao trong cảnh 3D

Với mỗi cặp phương trình:

- Hai mặt tường minh: `intersection_curves` trên lưới 2D, chính xác và giữ đúng z trên mặt thứ nhất.
- Mọi cặp còn lại: `implicit_surface_intersection` trên lưới 3D, dùng giá trị `F` của từng phương trình.

Hai nhánh này cho cùng một kiểu kết quả là danh sách đoạn thẳng trong tọa độ thế giới.

---

## 11. Giao diện một dòng, màu theo cặp và làm nổi bật (phiên bản 1.4)

- `plotting.PAIR_COLORS` và `plotting_3d.PairCurve` là nguồn màu duy nhất cho giao điểm và đường giao. `ui_focus.render_pair_line` đọc từ đây để tô màu chữ.
- Chế độ làm nổi bật là một tham số `focus_pairs: frozenset[str] | None` truyền vào `build_figure` và `build_scene_3d`. `None` nghĩa là không làm nổi bật. Các trace không được chọn giảm `opacity` xuống `DIM_OPACITY`, và chú thích của chúng trong suốt.
- Đường giao 3D được gộp theo cặp, mỗi cặp một trace `Scatter3d`. Nhờ vậy màu và độ dày có thể đặt riêng cho từng cặp.
- `ui_theme.render_header` dựng header bằng `st.columns` với `vertical_alignment="center"`. Badge canh phải bằng CSS `text-align: right`.
- Hộp thoại cú pháp dùng `st.dialog`, mở bằng nút trong sidebar. Hướng dẫn ngắn dùng `st.popover`.

---

## 12. Khung nhìn, canh khung và hiển thị số lượng lớn (phiên bản 2.x)

### 12.1 Thứ tự tính trong một lần vẽ 2D

Thứ tự này là quy tắc bắt buộc (`ui_2d.render_2d`, CLAUDE.md mục 18):

1. **Cửa sổ dò.** Trục tự canh dò trên `±200` (`SEARCH_HALF_WIDTH`). Trục cố định dò trên khung người dùng nhập, mở rộng bằng `viewport.domain_for`.
2. **Giao điểm.** Tính mọi cặp trên cửa sổ dò (mục 4.3 và 9.2).
3. **Canh khung x.** Nếu tự canh: `viewport.fit_view` lấy bao của giao điểm (đã lọc theo khung y nếu y cố định), có đệm 10% mỗi phía, rộng tối thiểu 12.
4. **Vẽ đường.** Đường được tính trên `domain_for(view_x)`. Đường ẩn nhờ vậy mịn khi xem gần.
5. **Canh khung y.** Nếu tự canh: khung y lấy từ đường và giao điểm trong khung x. Nếu khung vượt miền đã vẽ, đường được vẽ lại (tối đa `FRAME_PASSES = 4` lượt). Điều này ngăn đường tròn bán kính 50 bị cắt ở ±18.
6. **Nhãn và bảng.** Nhãn đặt sau khi khung đã cố định.

### 12.2 Đặt nhãn và giới hạn hiển thị

- `plotting.place_labels` thử 24 vị trí quanh mỗi điểm theo thứ tự ưu tiên. Vị trí nằm ngoài vùng vẽ hoặc chồng nhãn khác bị loại. Không có vị trí nào thì nhãn bị ẩn (trả về `None`), điểm vẫn có marker.
- Việc đặt nhãn có độ phức tạp khoảng bình phương số điểm, nên trên `MAX_LABELED_POINTS = 200` không đặt nhãn nào.
- Dòng liệt kê của một cặp chỉ hiện tọa độ khi có tối đa `MAX_LISTED_POINTS = 50` điểm. Bảng chỉ hiện khi có tối đa `MAX_TABLE_ROWS = 500` dòng; trên mức đó chỉ ghi số lượng.

### 12.3 Lỗi đã sửa và bài học

- **Khung đặt trước giao điểm.** Khung mặc định `±6` làm giao điểm `x ≈ −6.56` bị ẩn. Từ phiên bản 2.6, khung được canh sau khi có giao điểm.
- **Đoạn phẳng trong `|h|`.** Điểm trên đoạn `|h|` không đổi bị coi là cực tiểu, tạo hàng trăm nghìn ứng viên. Quy tắc cực tiểu dùng `<` ở phía phải để một đoạn phẳng chỉ cho một ứng viên.
- **Ngưỡng gộp quá lớn.** Gộp nghiệm dưới `1e-6` độ rộng miền làm mất cặp nghiệm cách nhau `3e-4` trên `±200`. Nay là `1e-9`.
- **Làm tròn nhãn.** Tọa độ tiếp điểm có sai số `1e-8`, nên ngưỡng làm tròn về 0 là `1e-6` (`implicit._snap_zero`). Ngưỡng `1e-10` cũ làm nhãn hiện `-0.0000`.
