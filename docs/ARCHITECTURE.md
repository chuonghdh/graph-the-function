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

**Quy tắc phụ thuộc:** `app.py` → `plotting` → `math_engine`. Không có chiều ngược. Nhờ vậy `math_engine` và `plotting` kiểm thử được mà không cần khởi động Streamlit.

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

### 4.3 Tìm giao điểm

Bài toán: tìm `x` sao cho `h(x) = f(x) - g(x) = 0` trên `[x_min, x_max]`.

1. **Lưới.** Lấy 2000 điểm đều và tính `h`.
2. **Ứng viên.** Tìm các cực tiểu địa phương của `|h|` trên lưới, bao gồm hai đầu mút. Điểm NaN không bao giờ là ứng viên.
3. **Thu hẹp.** Với mỗi ứng viên, chạy tìm kiếm tam phân trên `|h|` trong khoảng `[x_{i-1}, x_{i+1}]`, 100 vòng. Các khoảng được xử lý vector hóa cùng lúc.
4. **Xác nhận.** Chỉ nhận nghiệm khi `|h(x*)| ≤ 1e-9 · max(1, |f(x*)|, |g(x*)|)`. Bước này loại tiệm cận, nơi `|h|` nhỏ nhất trên lưới nhưng không tiến về 0.
5. **Gộp.** Sắp xếp và gộp các nghiệm cách nhau dưới `1e-6` độ rộng miền.
6. **Trùng hàm.** Nếu `|h|` gần 0 trên toàn bộ lưới, hai hàm trùng nhau, trả về rỗng.

**Vì sao không dùng dò đổi dấu (bisection):** dò đổi dấu bỏ sót tiếp xúc (`x²` với 0), và phải phân biệt tiệm cận với nghiệm thật. Cách tìm cực tiểu của `|h|` và xác nhận giá trị bắt được cả hai trường hợp bằng cùng một đường đi.

**Giới hạn đã biết:** Hai giao điểm nằm trong cùng một khoảng lưới (cách nhau dưới 1/2000 độ rộng miền) có thể bị bỏ sót. Với hàm dao động rất nhanh, cần tăng `samples`.

### 4.4 Khung tung độ và cắt gián đoạn

- Khung `y` dùng phân vị 2% và 98% của mọi giá trị hữu hạn, thay vì min/max. Nhờ vậy `tan(x)` không ép đồ thị còn lại thu nhỏ.
- Khung luôn bao gồm tung độ các giao điểm, và được đệm 10%.
- Hai mẫu liền kề cách nhau quá `2 × chiều cao khung` được coi là tiệm cận. Điểm sau được đặt thành NaN.

---

## 5. Trạng thái và hiệu năng

- **Không lưu trạng thái phía server.** Mọi kết quả được tính lại mỗi lần chạy script. Đo cục bộ với ba hàm, 1500 điểm mỗi hàm và 7 giao điểm: khoảng 30 ms cho mỗi lần vẽ sau lần chạy đầu (lần đầu khoảng 265 ms do khởi tạo).
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
app.py ── radio "view_mode" ──┬──▶ graph_app/ui_2d.py ──▶ math_engine, plotting
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

Giới hạn: nội suy tuyến tính giữa các đỉnh lưới làm sai số vị trí đường giao cỡ bước lưới. Tăng độ phân giải để giảm sai số.

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
| 2D: hai `y = f(x)` | Cực tiểu của `|f − g|` + tam phân (`math_engine`) | Chính xác, nhanh, bắt được tiếp xúc |
| 2D: có đường ẩn | Ô lưới có cả F và G đổi dấu → nghiệm tuyến tính → Newton trên `F = G = 0` (`implicit`) | Không cần chia theo x; xử lý được đường cong bất kỳ |
| 3D: hai mặt ẩn | Mỗi voxel có cả F và G đổi dấu → giao hai mặt phẳng xấp xỉ → cắt theo biên voxel | Vectơ hóa bằng NumPy, không cần vòng lặp Python |

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
