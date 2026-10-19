# Đặc tả yêu cầu sản phẩm (SPEC)

Tác giả vai trò: Product Owner cum BA.
Phiên bản: 1.0.

---

## 1. Mục tiêu

Xây dựng ứng dụng web cho phép người dùng nhập hàm số dạng `y = f(x)`, vẽ đồ thị 2D theo thời gian thực, so sánh tối đa ba hàm trên cùng một khung, và tự động tìm, đánh dấu cùng chú thích tọa độ các điểm giao nhau.

Người dùng mục tiêu: học sinh, sinh viên và giáo viên toán cần vẽ nhanh và trực quan các hàm số để kiểm tra nghiệm, so sánh hành vi.

---

## 2. Tính năng

### F1. Nhập hàm số `y = f(x)`

- Người dùng gõ biểu thức theo biến `x` vào một trong ba ô `f1(x)`, `f2(x)`, `f3(x)`.
- Hỗ trợ đa dạng hàm toán học: đa thức, lượng giác, mũ, logarit, căn thức, trị tuyệt đối, hyperbolic. Chi tiết cú pháp ở mục 4.
- Ô rỗng nghĩa là không vẽ hàm đó.
- Lỗi cú pháp hoặc ký tự không được phép hiển thị thông báo tiếng Việt ngay dưới ô nhập, không làm sập ứng dụng.

**Tiêu chí chấp nhận:**
- [ ] Nhập `x^3 - 2*x + 1` và `sin(x)/x` đều vẽ đúng.
- [ ] Nhập `__import__('os')` hoặc `open('f')` bị từ chối với thông báo lỗi, không thực thi gì.
- [ ] Nhập `a*x` (có biến khác `x`) bị từ chối và thông báo tên biến không hợp lệ.
- [ ] Nhập biểu thức trên 200 ký tự bị từ chối.

### F2. Vẽ tối đa ba hàm số cùng lúc

- Ba hàm có thể vẽ đồng thời trên cùng một hệ trục để so sánh.
- Mỗi hàm có một màu riêng, lấy từ bảng màu cố định (xem mục 5).
- Người dùng chỉnh khoảng hiển thị trục x bằng thanh trượt ở thanh bên (sidebar), từ -100 đến 100.

**Tiêu chí chấp nhận:**
- [ ] Ba hàm được vẽ với ba màu khác nhau, chú thích đúng tên `f1(x) = ...`.
- [ ] Đổi khoảng trục x, đồ thị vẽ lại theo khoảng mới mà không cần tải lại trang.

### F3. Cập nhật thời gian thực

- Mỗi lần người dùng đổi hàm, nhấn Enter trong ô nhập hoặc kéo thanh trượt, đồ thị và bảng giao điểm được tính lại ngay.
- Mục tiêu thời gian phản hồi: dưới 1 giây với ba hàm và khoảng x mặc định.

**Tiêu chí chấp nhận:**
- [ ] Kéo thanh trượt, đồ thị cập nhật mà không cần bấm nút nào khác.
- [ ] Ba hàm và khoảng x mặc định phản hồi trong dưới 1 giây trên máy thông thường.

### F4. Phân tích điểm giao nhau

- Với mỗi cặp hàm đã nhập, ứng dụng tìm mọi điểm giao trong khoảng x đang hiển thị.
- Mỗi giao điểm được đánh dấu bằng một chấm trắng và có chú thích ghi cặp hàm cùng tọa độ `(x; y)`, làm tròn đến 4 chữ số thập phân.
- Dưới đồ thị có bảng liệt kê toàn bộ giao điểm theo cặp hàm.
- Các trường hợp đặc biệt:
  - **Tiếp xúc** (ví dụ `x²` và trục hoành tại 0): tính là một giao điểm.
  - **Tiệm cận** (ví dụ `1/x` đổi dấu tại 0): không tính là giao điểm.
  - **Hai hàm song song** (ví dụ `x+1` và `x+2`): không có giao điểm.
  - **Hai hàm trùng nhau** (ví dụ `x` và `x`): có vô số giao điểm, ứng dụng không liệt kê và hiển thị thông báo không tìm thấy giao điểm rời rạc.

**Tiêu chí chấp nhận:**
- [ ] `x^2 - 2` và `sin(x)` có hai giao điểm trong khoảng [-10, 10] (xấp xỉ x = -1.0615 và x = 1.7285).
- [ ] `1/x` và `0` không có giao điểm.
- [ ] Mỗi chú thích giao điểm hiển thị đúng định dạng `(x; y)`.
- [ ] Khi không có giao điểm, bảng hiển thị thông báo rõ ràng.

### F5. Giao diện Dark Mode

- Nền tối (`#0E1117`), chữ sáng, thanh bên cùng tông màu.
- Đồ thị dùng template tối, nền trong suốt, lưới mờ, để hòa vào giao diện.
- Một thanh màu bên trái mỗi ô nhập cho biết đường đồ thị tương ứng có màu gì.

**Tiêu chí chấp nhận:**
- [ ] Toàn bộ giao diện hiển thị nền tối khi mở ứng dụng.
- [ ] Ba đường đồ thị có ba màu khác nhau và khớp với thanh màu của ô nhập tương ứng.

### F6. Triển khai

- Mã nguồn chạy được trên máy cục bộ bằng một lệnh.
- Mã nguồn deploy được lên Streamlit Community Cloud và truy cập qua link công khai, không cần cấu hình thêm ngoài việc chọn file `app.py`.

**Tiêu chí chấp nhận:**
- [ ] `pip install -r requirements.txt` cài được đầy đủ thư viện không lỗi.
- [ ] `streamlit run app.py` mở được ứng dụng.
- [ ] Mã nguồn không chứa khóa bí mật; `.gitignore` loại bỏ môi trường ảo và file cache.

### F7. Chế độ đồ thị 3D: z = f(x, y) (phiên bản 1.1)

- Thanh chuyển chế độ ở đầu trang: **"Đồ thị 2D (y = f(x))"** và **"Đồ thị 3D (z = f(x, y))"**. Chế độ 2D giữ nguyên hành vi của phiên bản 1.0.
- Nhập tối đa **hai mặt** `z1`, `z2` theo hai biến `x` và `y`. Ví dụ: `x^2 + y^2`, `sin(sqrt(x^2 + y^2))`, `x*cos(y)`.
- Mặt được vẽ bằng `go.Surface`. Người dùng xoay 360 độ, phóng to thu nhỏ, và di chuột để xem tọa độ `(x, y, z)` ngay khi di chuyển.
- Sidebar có **khoảng Min–Max cho trục x và y**, cùng **độ phân giải lưới** (20 đến 200 điểm mỗi chiều, mặc định 100).
- Mỗi mặt chọn được một bảng màu: **Viridis, Plasma, Turbo, Electric**.
- Điểm không xác định (chia 0, căn số âm) bị ẩn khỏi mặt, và có ghi chú số điểm đã ẩn.

**Tiêu chí chấp nhận:**
- [ ] Chuyển qua lại giữa 2D và 3D không gây lỗi. Mỗi chế độ có ô nhập riêng; nội dung ô nhập của chế độ kia có thể bị làm mới khi quay lại, đây là hành vi đã chấp nhận của Streamlit.
- [ ] `x^2 + y^2` và `sin(sqrt(x^2 + y^2))` vẽ được thành mặt, xoay và phóng to được.
- [ ] Nhập `x*w` hoặc `x*y` trong chế độ 2D bị từ chối với thông báo rõ ràng.
- [ ] Thay đổi Min–Max của x hoặc y làm mặt vẽ lại đúng khoảng.
- [ ] `1/(x*y)` vẽ được, các điểm chia cho 0 bị ẩn, không làm sập ứng dụng.

### F8. Đường giao giữa hai mặt 3D (phiên bản 1.1)

- Khi người dùng nhập đủ hai mặt, ứng dụng tính **đường giao** là tập điểm mà z₁ = z₂ và đánh dấu bằng đường màu trắng nổi trên hai mặt.
- Mỗi điểm của đường giao nằm chính xác trên mặt thứ nhất.
- Phần thông báo cho biết số đường giao và số điểm đã tô sáng. Khi hai mặt không cắt nhau hoặc trùng nhau, thông báo tương ứng được hiển thị.

**Tiêu chí chấp nhận:**
- [ ] `sin(sqrt(x^2 + y^2))` và `0.3*x + 0.1*y` có đường giao được đánh dấu.
- [ ] Hai mặt phẳng song song hiển thị thông báo không cắt nhau.
- [ ] Hai mặt trùng nhau không liệt kê hàng nghìn đường giả.

**Ngoài phạm vi phiên bản 1.1:** hàm ẩn F(x, y, z) = 0, tọa độ trụ và cầu, xuất ảnh 3D.

---

## 3. Ngoài phạm vi (phiên bản 1.0)

- Vẽ hàm tham số `x(t), y(t)` và hàm ẩn `F(x, y) = 0`.
- Vẽ hàm theo tọa độ cực.
- Lưu hoặc chia sẻ đồ thị, xuất ra PNG/SVG.
- Đăng nhập, tài khoản người dùng.
- Biến thứ hai, tham số hóa bằng thanh trượt.
- Nghiệm phức. Chỉ xét miền số thực.

---

## 4. Định dạng nhập liệu hàm số

Đầu vào là chuỗi văn bản một dòng, chỉ dùng biến `x`. Bộ phân tích dùng SymPy với danh sách tên được phép, không gọi `eval` trực tiếp.

| Nhóm | Cú pháp | Ghi chú |
|------|---------|---------|
| Phép toán | `+ - * /` | |
| Lũy thừa | `x^2` hoặc `x**2` | `^` được đổi thành `**` |
| Nhân ẩn | `2x`, `2sin(x)` | Tương đương `2*x`, `2*sin(x)` |
| Lượng giác | `sin cos tan cot sec csc` | Đơn vị radian |
| Lượng giác ngược | `asin acos atan` (hoặc `arcsin arccos arctan`) | Miền giá trị hạn chế |
| Hyperbolic | `sinh cosh tanh` | |
| Mũ | `exp(x)`, `e^x` | |
| Logarit | `log(x)` hoặc `ln(x)` | **Logarit tự nhiên** |
| Logarit cơ số | `log10(x)`, `log2(x)` | Dùng `log10` cho cơ số 10 |
| Căn | `sqrt(x)` | Chỉ xác định khi x ≥ 0 |
| Trị tuyệt đối | `abs(x)` | |
| Hằng số | `pi` hoặc `π`, `e` | |

**Quy ước về miền xác định trên số thực:**
- Chia cho 0, `log` của số ≤ 0, `sqrt` của số âm: không xác định, đường vẽ bị ngắt tại đó.
- Căn bậc chẵn hoặc lũy thừa phân số của số âm (ví dụ `x^(1/3)` với x < 0): không xác định, vì miền là số thực. Đây là giới hạn đã chấp nhận ở phiên bản 1.0.
- Tiệm cận (như `tan` tại π/2): đường vẽ bị ngắt, không nối qua tiệm cận.

---

## 5. Bảng màu

| Hàm | Màu | Mã |
|-----|-----|----|
| f1 | Xanh lam sáng | `#00E5FF` |
| f2 | Hồng đỏ | `#FF4D6D` |
| f3 | Vàng | `#FFD60A` |
| Giao điểm | Trắng | `#FFFFFF` |

---

## 6. Bố cục màn hình

```
┌──────────────┬────────────────────────────────────────────────────┐
│ THANH BÊN    │  📈 Vẽ đồ thị hàm số 2D                             │
│              │  ┌────────────┬────────────┬────────────┐           │
│ Khoảng x     │  │ ▌f1(x) =   │ ▌f2(x) =   │ ▌f3(x) =   │           │
│ [-10 ──● 10] │  │ [x^2 - 2 ] │ [sin(x)  ] │ [         ]│           │
│              │  └────────────┴────────────┴────────────┘           │
│ ▸ Hướng dẫn  │  ┌──────────────────────────────────────────────┐  │
│              │  │          ĐỒ THỊ (có chú thích giao điểm)      │  │
│              │  └──────────────────────────────────────────────┘  │
│              │  Điểm giao nhau: bảng cặp hàm, x, y                 │
└──────────────┴────────────────────────────────────────────────────┘
```

Trên điện thoại, ba ô nhập xếp dọc, thanh bên thu gọn.

---

## 7. Tiêu chí nghiệm thu tổng thể

- [ ] Mọi tiêu chí chấp nhận F1 đến F6 đạt.
- [ ] `python -m pytest` pass toàn bộ.
- [ ] Ứng dụng khởi chạy không lỗi với `streamlit run app.py`.
- [ ] README hướng dẫn đủ các bước chạy local và deploy.

---

## 8. Phiên bản 1.2: phương trình ẩn và UI/UX

### F9. Đường ẩn 2D: f(x, y) = g(x, y)

- Người dùng nhập phương trình tự do ở ô f1, f2 hoặc f3. Ví dụ: `x^2 + y^2 = 25`, `x^2/9 + y^2/4 = 1`, `sin(x) = cos(y)`.
- Hệ thống chuyển `A = B` thành `F = A − B = 0` và vẽ đường mức 0 bằng contour.
- Phương trình dạng `y = g(x)` vẫn được vẽ như hàm số, không đi qua contour.
- Khi nhập phương trình có `y`, mà không có dấu `=`, hệ thống hiểu là `F = 0`. Ví dụ `x^2 + y^2 - 25`.
- Khung y có hai chế độ: tự động theo hàm, hoặc cố định theo thanh trượt Min–Max. Đường ẩn luôn được dò trong khung y đã chọn.

**Tiêu chí chấp nhận:**
- [ ] `x^2 + y^2 = 25` vẽ đường tròn bán kính 5, sai số bán kính dưới 1e-3.
- [ ] `x^2/9 + y^2/4 = 1` vẽ elip đóng.
- [ ] `sin(x) = cos(y)` vẽ được nhiều đường tách rời.
- [ ] `x <= 2` bị từ chối với thông báo bất đẳng thức chưa được hỗ trợ.

### F10. Mặt ẩn 3D: F(x, y, z) = 0

- Chế độ 3D có thêm bộ chọn kiểu: **Mặt z = f(x, y)** (như phiên bản 1.1) hoặc **Mặt ẩn F(x, y, z) = 0**.
- Tối đa ba mặt ẩn, mỗi mặt một bảng màu. Vẽ bằng `go.Isosurface` tại mức 0.
- Sidebar có khoảng Min–Max cho x, y, z và độ phân giải lưới từ 15 đến 60 điểm mỗi chiều.
- Ví dụ hợp lệ: `x^2 + y^2 + z^2 = 25` (mặt cầu), `x^2 + y^2 = 9` (hình trụ), `x^2 + y^2 - z^2 = 0` (hình nón).

**Tiêu chí chấp nhận:**
- [ ] Mặt cầu và hình trụ mặc định vẽ được, xoay và phóng to được.
- [ ] Hai mặt ẩn có đường giao được tô màu trắng và báo cáo số đoạn.
- [ ] Mặt ẩn có điểm không xác định không làm sập ứng dụng.

### F11. Giao điểm và đường giao (mở rộng)

- Giao điểm 2D giữa hai phương trình ẩn được tìm bằng hệ phương trình `F = G = 0`, tinh chỉnh bằng Newton.
- Đường giao 3D giữa hai mặt ẩn được xấp xỉ theo từng voxel. Sai số vị trí cỡ bước lưới.
- Nếu hai phương trình trùng nhau hoàn toàn, hệ thống không liệt kê vô số điểm.

### F12. Thiết kế giao diện và trợ giúp nhập liệu (UI/UX)

- **Dark Mode chuẩn:** nền `#0E1117`, chữ `#E6EDF3`, ô nhập font đơn cách, viền neon khi focus.
- **Bảng màu neon 2D:** Cyan `#00F0FF`, Magenta `#FF2BD6`, Vàng sáng `#FFEA00`.
- **Chống chồng chữ:** chú thích giao điểm được đặt theo thuật toán tham lam, thử lần lượt 12 vị trí quanh điểm và chọn vị trí không chồng.
- **Math Syntax Helper:** bảng cú pháp ở thanh bên, có mục "Lỗi thường gặp" với các ví dụ `x2` → `x^2`, `xy` → `x*y`.
- **Lỗi thân thiện:** thông báo lỗi có tên ô, mô tả rõ, và gợi ý sửa khi đoán được ý người dùng.

**Tiêu chí chấp nhận:**
- [ ] Ba đường 2D có ba màu neon khác nhau và khớp thanh màu của ô nhập.
- [ ] Bốn giao điểm sát nhau có chú thích không chồng lên nhau.
- [ ] `xy = 1` báo lỗi kèm gợi ý `x*y`.
- [ ] Dùng `z` ở chế độ 2D báo lỗi kèm gợi ý chuyển sang chế độ 3D.


---

## 9. Phiên bản 1.3: tự động nhận diện, không còn nút chọn chế độ

Phiên bản này thay thế cách chọn chế độ thủ công ở F7 và F10. Các yêu cầu về hình học, thuật toán và
bảng màu vẫn giữ nguyên.

### F13. Nhận diện không gian tự động

- Mọi ô nhập đều ở thanh bên. Không có radio hay tab để chọn 2D hoặc 3D.
- Nếu không ô nào chứa biến `z`, hệ thống ở chế độ 2D. Nếu có ít nhất một ô chứa `z`, cả hệ thống chuyển sang 3D.
- Badge `[TỰ ĐỘNG DETECT] Chế độ Đồ thị 2D` hoặc `... 3D` hiển thị ngay phía trên đồ thị.
- Ô có `z` nhưng viết sai vẫn đưa hệ thống sang 3D, để lỗi hiện đúng trong ngữ cảnh 3D.

**Tiêu chí chấp nhận:**
- [ ] Gõ `x^2 - 2` rồi gõ thêm `z = x*y` ở ô khác: badge đổi sang 3D không cần thao tác nào khác.
- [ ] Xóa mọi hàm có `z`: badge trở về 2D.
- [ ] `z2 + x = 1` (gõ thiếu `^`) báo lỗi tên `z2` kèm gợi ý `z^2`.

### F14. Cú pháp linh hoạt

| Dạng nhập | Ví dụ | Hệ thống hiểu là |
|---|---|---|
| Hàm tường minh | `y = x^2 + 2x + 1` | đồ thị 2D |
| Hàm không có vế trái | `sin(x)` | `y = sin(x)` |
| Mặt tường minh | `z = x^2 + y^2` | mặt 3D |
| Đẳng thức | `x^2 + y^2 = 25`, `sin(x) = cos(y)` | đường ẩn 2D |
| Đẳng thức 3D | `x^2 + y^2 + z^2 = 16` | mặt ẩn 3D |
| Biểu thức đơn | `x^2 + y^2 - 25` | `x^2 + y^2 - 25 = 0` |

- Phương trình `A = B` luôn được đưa về `F = A − B = 0`.
- Trong cảnh 3D, `y = g(x)` và đường ẩn 2D được vẽ thành mặt trụ đứng.

### F15. Cheatsheet và thông báo lỗi

- Thanh bên có cheatsheet cú pháp: `^` hoặc `**` để lũy thừa, `*` để nhân, `=` cho phương trình.
- Lỗi cú pháp chỉ rõ ô nào sai (`f1`, `f2`, `f3`). Nếu đoán được ý người dùng, lỗi kèm gợi ý sửa.

---

## 10. Phiên bản 1.4: tối ưu giao diện và giao điểm

### F16. Header một dòng

- Tiêu đề bên trái, nút `(i)` ở giữa, badge trạng thái canh phải trên cùng một hàng.
- Hướng dẫn nhập liệu nằm trong popover `(i)`, chỉ mở khi người dùng bấm.
- Khoảng trắng phía trên trang được thu gọn tối đa.

### F17. Sidebar gọn

- Ba ô nhập ở đầu. Ngay bên dưới là nút "📖 Hướng dẫn cú pháp", mở hộp thoại cheatsheet.
- Phạm vi trục, khung y, độ phân giải và bảng màu gom vào "⚙️ Cấu hình phạm vi & màu sắc", mặc định thu gọn.

### F18. Màu theo cặp giao

- Mỗi cặp giao có một màu cố định: `f1 ∩ f2` cam vàng, `f1 ∩ f3` xanh lá neon, `f2 ∩ f3` tím neon.
- Điểm giao, đường giao 3D và chú thích của cặp dùng cùng màu. Màu chữ của dòng thông báo cũng trùng màu đó.

### F19. Văn bản giao tuyến theo chuẩn toán học

- Dạng thông báo: `f1 ∩ f2: Biểu diễn qua phương trình giao tuyến: <A> và <B>.`
- Không dùng cụm từ "được tô sáng" trong bất kỳ thông báo nào.

### F20. Làm nổi bật (Focus Mode)

- Công tắc "✨ Highlight đường giao / điểm giao" và bộ chọn cặp cần làm nổi bật.
- Khi bật: cặp được chọn phóng to và rõ. Đường cong gốc, mặt gốc và các cặp khác giảm độ mờ xuống mức trong suốt.
- Nếu bật nhưng không chọn cặp nào, đồ thị hiển thị bình thường.

**Tiêu chí chấp nhận:**
- [ ] Bật làm nổi bật rồi chọn `f1 ∩ f2`: đường cong và mặt gốc mờ, đường giao cam dày hơn.
- [ ] Bỏ hết cặp chọn: không lỗi, không làm mờ toàn bộ.
- [ ] Không có thông báo nào chứa cụm "được tô sáng".

> **Ghi chú (phiên bản 1.5 trở đi):** công tắc chung ở F20 đã bỏ. Làm nổi bật nay là checkbox cho từng cặp, xem F25.

---

## 11. Phiên bản 1.5 đến 2.8: các yêu cầu hiện hành

Phần này mô tả trạng thái hiện tại. Mục nào thay thế mục cũ đều ghi rõ.

### F21. Nhập động từ 2 đến 6 hàm

- Mặc định có hai ô `f1`, `f2`. Nút "➕ Thêm hàm số" thêm ô, tối đa sáu. Mỗi ô có ✖ để xóa, tối thiểu còn hai ô.
- Xóa một ô không làm mất nội dung các ô khác (mỗi ô có mã định danh ổn định).

**Tiêu chí chấp nhận:**
- [ ] Thêm đến sáu ô, nút thêm bị vô hiệu hóa ở ô thứ sáu.
- [ ] Xóa ô giữa, nội dung ô còn lại không đổi.

### F22. Cú pháp mở rộng

- Thêm `|x|`, `pi` hoặc `π`, `e`, `e^x`, `^`, nhân ẩn `2x`.
- Phương trình ẩn `A = B` được đổi thành `A − B = 0`.

**Tiêu chí chấp nhận:**
- [ ] `|x| - 1` và `sin(pi*x)` vẽ được.
- [ ] `x2` gợi ý `x^2`, `xy` gợi ý `x*y`.

### F23. Thanh legend trên đồ thị

- Mỗi hàm có một checkbox nằm trên đồ thị, mặc định tích.
- Bỏ tích làm mờ đường hoặc mặt của hàm đó và mọi cặp có liên quan.

**Tiêu chí chấp nhận:**
- [ ] Bỏ tích `f2`: đường `f2` và các giao điểm có `f2` mờ, các hàm khác không đổi.

### F24. 20 hàm số nổi tiếng

- 10 đường 2D và 10 mặt 3D (`graph_app/presets.py`).
- Mỗi ô nhập có một biểu tượng 📚 mở danh sách mẫu. Chọn mẫu điền vào đúng ô đó.
- Mặt trụ dùng dạng `x**2 + y**2 = 9 + sin(z)**2 + cos(z)**2 - 1` để SymPy không tự rút gọn `z` đi.

**Tiêu chí chấp nhận:**
- [ ] Có đủ 20 mẫu, mỗi mẫu biên dịch được và cho đúng chiều (2D hoặc 3D).
- [ ] Chọn mẫu cho `f2` không đổi `f1`.

### F25. Làm nổi bật theo từng cặp (thay F20)

- Dưới đồ thị, mỗi cặp giao có một hàng: checkbox, tên cặp và danh sách tọa độ.
- Tích checkbox: cặp đó phóng to, các đường và cặp khác mờ đi.
- Cặp không có giao điểm hiện checkbox bị vô hiệu hóa.

**Tiêu chí chấp nhận:**
- [ ] Tích `f1 ∩ f2`: đường giao của cặp dày hơn, các cặp khác mờ.
- [ ] Cặp không có giao điểm: checkbox không bấm được.

### F26. Phạm vi trục bằng ô nhập số

- Mỗi trục có hai ô `min` và `max`. Ô `min` phải nhỏ hơn `max`, nếu không ứng dụng báo lỗi và không vẽ.
- Trục y có công tắc "Tự co giãn khung y" (mặc định bật). Trục x có công tắc "Tự canh khung x theo giao điểm" (mặc định bật).
- Trục tung của đồ thị 2D luôn hiển thị rõ, có đường trục, tên trục và vạch chia.

**Tiêu chí chấp nhận:**
- [ ] `min = 7`, `max = 6` với canh khung tắt: báo lỗi, không vẽ.
- [ ] Trục y rõ ràng trên nền tối.

### F27. Canh khung theo giao điểm (thay cho khung cố định)

- Giao điểm được tính trước, trên cửa sổ dò `±200`. Sau đó mới canh khung x để chứa mọi giao điểm, rồi canh khung y theo đồ thị và giao điểm.
- Khung x canh bằng bao của giao điểm, có đệm 10% mỗi phía và rộng tối thiểu 12 đơn vị.
- Khi khung y tự co giãn, giao điểm không bị lọc theo khoảng y cũ.
- Hai hàm trùng nhau trên một đoạn (vô số giao điểm) không được dùng để canh khung.

**Tiêu chí chấp nhận:**
- [ ] `x^2 + 4*x - 15` và `x*sin(x)` hiện đủ hai giao điểm `(-6.5597; 1.7907)` và `(2.5235; 1.4623)`, dù khung nhập mặc định là `±6`.
- [ ] `x^2 - 2` và `20` có giao điểm ở `y = 20`: giao điểm hiện và khung y bao được nó.
- [ ] `x` và `x` không làm khung lệch khỏi `±6`.

### F28. Giao điểm 2D chính xác

- Hiệu `f − g` là đa thức thì giải đúng bằng SymPy, gồm cả nghiệm bội.
- Hàm khác: dò đổi dấu trên `samples` đoạn con, rồi chia đôi trên NumPy. Cặp nghiệm nằm trong cùng một ô lưới được bắt bằng đỉnh parabol và cực trị của `h`.
- Tiếp xúc (không đổi dấu) được bắt bằng cực tiểu của `|h|`.
- Mọi ứng viên đều được kiểm tra lại `|f − g| ≤ 1e-9` tại điểm đó. Điểm gián đoạn như tiệm cận của `1/x` bị loại.
- Nghiệm ở mép miền xác định (như `√x = x/2` tại 0) được tìm riêng, với ngưỡng 1e-6.

**Tiêu chí chấp nhận:**
- [ ] `sin(100x)` có đúng 12733 nghiệm trên `[-200, 200]`.
- [ ] `1/x = x` cho `±1`, không cho điểm tại tiệm cận.
- [ ] `√x = x/2` cho `(0, 0)` và `(4, 2)`.

### F29. Giao điểm 2D của đường ẩn, gồm tiếp xúc

- Giao cắt: lưới ô, giải tuyến tính rồi Newton, kiểm tra phần dư.
- Tiếp xúc: cực tiểu của `F² + G²` rồi Levenberg–Marquardt. Nhánh này bắt được tiếp xúc mà lưới không thấy.

**Tiêu chí chấp nhận:**
- [ ] `x^2 + y^2 = 25` với `y = 5` cho `(0, 5)`.
- [ ] `y = x²` với tiếp tuyến `2x - y - 1 = 0` cho `(1, 1)`.
- [ ] `x^2 + y^2 = 25` với `y = 5.001` không cho điểm nào (không âm tính giả).

### F30. Đường giao 3D chính xác và điểm tiếp xúc

- Đường giao hai mặt tường minh: các điểm được chiếu về `f₁ − f₂ = 0` và z = f₁(x, y). Sai số khoảng `1e-16`.
- Đường giao hai mặt ẩn: đầu mút đoạn voxel được chiếu về `{F = 0, G = 0}`. Sai số khoảng `1e-16`.
- Điểm tiếp xúc giữa hai mặt ẩn được tìm và vẽ bằng marker riêng. Sai số khoảng `1e-8` vì là nghiệm kép.

**Tiêu chí chấp nhận:**
- [ ] `x² + y² + z² = 1` với `z = 1` cho điểm `(0, 0, 1)` có marker.
- [ ] Paraboloid `z = x² + y²` với `z = 4` cho đường tròn bán kính 2, sai số dưới `1e-9`.

### F31. Hiển thị số lượng lớn

- Quá 200 giao điểm: không gắn nhãn, mọi điểm vẫn có marker.
- Quá 50 giao điểm của một cặp: chỉ hiện số lượng, không liệt kê tọa độ.
- Quá 500 dòng: bảng không hiện, chỉ có dòng ghi số lượng.

**Tiêu chí chấp nhận:**
- [ ] `sin(60x)` và `0.2` trên `±200` (khoảng 7600 giao điểm): không lỗi, không có nhãn, có dòng ghi số lượng.

### Giới hạn đã biết (không thuộc phạm vi các phiên bản này)

- Thay đổi khung bằng chuột trong trình duyệt (zoom, pan) không kích hoạt tính lại. Streamlit không gửi sự kiện này về Python.
- Tiếp tuyến tại một điểm của đường cong chưa được triển khai. Nó sẽ dùng cùng gradient với F29.
- Tiếp xúc giữa hai mặt tường minh 3D chưa được đánh dấu bằng điểm.
