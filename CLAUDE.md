# CLAUDE.md — Sổ tay quy chuẩn dự án

Dự án: **Ứng dụng web vẽ đồ thị hàm số 2D** (Python + Streamlit + Plotly + SymPy + NumPy).
Mục tiêu: mã nguồn sẵn sàng deploy lên **Streamlit Community Cloud** (link public).

---

## 1. Quy trình làm việc của 6 Agents

Đội ngũ gồm 7 vai trò (phiên bản 1.2 thêm UI/UX Specialist). Mỗi vai trò là một "chiếc mũ" được đội trưởng (Orchestrator) giao việc theo thứ tự dưới đây.
Mỗi vai trò chỉ được sửa đúng nhóm file thuộc phạm vi của mình, trừ khi Orchestrator cho phép.

| # | Vai trò | Trách nhiệm chính | Sản phẩm bàn giao | Phạm vi file |
|---|---------|-------------------|-------------------|--------------|
| 1 | 👑 Orchestrator (PM) | Phân tích yêu cầu, tạo cấu trúc dự án, chia task, theo dõi tiến độ, quyết định khi có xung đột | `CLAUDE.md`, cấu trúc thư mục, tổng hợp báo cáo | `CLAUDE.md`, thư mục gốc |
| 2 | 💡 Product Owner cum BA | Viết đặc tả UI/UX, định nghĩa cú pháp nhập hàm số, tiêu chí chấp nhận | `docs/SPEC.md` | `docs/SPEC.md` |
| 3 | 🔍 Researcher & Architect | Chọn thư viện, thiết kế kiến trúc mô-đun (tách logic toán và giao diện) | `docs/ARCHITECTURE.md` | `docs/ARCHITECTURE.md` |
| 4 | 💻 Lead Python Developer | Viết mã nguồn, xử lý ngoại lệ toán học, `requirements.txt`, `.gitignore` | `app.py`, `graph_app/`, `.streamlit/config.toml` | `app.py`, `graph_app/`, `.streamlit/`, `requirements*.txt`, `.gitignore` |
| 5 | 🧪 QA / Tester | Viết unit test, chạy ứng dụng, bắt lỗi cú pháp / nhập liệu / đồ thị | `tests/`, `pytest.ini` | `tests/`, `pytest.ini` |
| 6 | 🎭 UI/UX Specialist | Dark Mode chuẩn (#0E1117), chống chồng chữ (label, chú thích), bảng màu neon, thông báo lỗi thân thiện | `graph_app/ui_theme.py`, `graph_app/ui_help.py`, quy tắc đặt nhãn trong `plotting.py` | `graph_app/ui_theme.py`, `graph_app/ui_help.py`, `.streamlit/config.toml` |
| 7 | 🛡️ Code Reviewer & Deploy | Review code (sạch, có comment, đúng Dark Mode), viết README, kiểm tra điều kiện deploy | `README.md`, báo cáo review | `README.md` (sửa code chỉ khi Orchestrator duyệt) |

### Luồng bàn giao

```
Orchestrator → PO/BA → Researcher/Architect → Lead Dev → QA → Reviewer/Deploy → Orchestrator (nghiệm thu)
                                                    ↑                 │
                                                    └──── lỗi ────────┘
```

1. **Orchestrator** khởi tạo `CLAUDE.md` và cấu trúc thư mục, giao task cho PO.
2. **PO/BA** viết `docs/SPEC.md`. Phải có tiêu chí chấp nhận (acceptance criteria) cho từng tính năng.
3. **Researcher/Architect** viết `docs/ARCHITECTURE.md`, chốt phiên bản thư viện, tách module.
4. **Lead Dev** viết code theo kiến trúc. Mỗi lần hoàn thành một module, tự chạy `python -m pytest` trước khi bàn giao.
5. **QA** viết test theo tiêu chí trong `SPEC.md`. Chạy ứng dụng với `streamlit run app.py`, ghi lại lỗi và gửi lại Lead Dev.
6. **Reviewer/Deploy** rà soát code theo checklist ở mục 5, viết `README.md`, xác nhận `requirements.txt` đủ điều kiện deploy.
7. **Orchestrator** nghiệm thu: tất cả test pass, ứng dụng chạy được, đúng tiêu chí chấp nhận.

### Quy tắc phối hợp

- Lỗi do QA phát hiện được Lead Dev sửa; không tự ý sửa test để "cho qua". Test chỉ được đổi khi đặc tả đổi.
- Mọi thay đổi về phạm vi tính năng phải quay về PO/BA và được Orchestrator duyệt.
- Không commit hoặc push Git khi chưa có yêu cầu rõ ràng của người dùng.

---

## 2. Môi trường, cài đặt, test và chạy

Yêu cầu: **Python 3.12** (khuyến nghị; tối thiểu 3.11).

### Cài đặt

```powershell
# Tạo môi trường ảo (một lần)
python -m venv venv

# Kích hoạt (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Cài thư viện runtime + phát triển
pip install -r requirements-dev.txt
```

Khi thêm thư viện mới: cài bằng pip, rồi cập nhật đúng file (`requirements.txt` cho runtime, `requirements-dev.txt` cho test). Ghi phiên bản cố định (`==`), vì Streamlit Cloud cần build lặp lại được.

### Test

```powershell
# Chạy toàn bộ unit test và smoke test
python -m pytest

# Chạy một file cụ thể, hiển thị chi tiết
python -m pytest tests/test_math_engine.py -v
```

### Khởi chạy ứng dụng

```powershell
streamlit run app.py
```

Mặc định ứng dụng mở tại `http://localhost:8501`.

---

## 3. Quy chuẩn viết code Python

### 3.1 Phong cách chung (Clean Code)

- Tuân thủ **PEP 8**, độ dài dòng tối đa **100 ký tự**.
- Tên biến, hàm, module: `snake_case`. Tên lớp: `PascalCase`. Hằng số: `UPPER_SNAKE_CASE`.
- Hàm ngắn, làm một việc. Tối đa khoảng 40 dòng cho mỗi hàm; quá dài thì tách ra.
- Không dùng số "ma thuật": đặt thành hằng số có tên, kèm chú thích đơn vị hoặc ý nghĩa.
- Không để `except:` trần. Bắt đúng loại ngoại lệ.
- Không dùng `eval` / `exec` trực tiếp trên dữ liệu người dùng. Mọi chuỗi nhập vào phải đi qua bộ phân tích an toàn trong `graph_app/math_engine.py`.
- Mỗi module chỉ import những gì nó dùng.

### 3.2 Type hinting (bắt buộc)

- Mọi hàm và phương thức công khai phải có đầy đủ type hint cho tham số và giá trị trả về.
- Dùng `from __future__ import annotations` ở đầu mỗi module.
- Dùng cú pháp hiện đại: `list[float]`, `tuple[str, ...]`, `X | None`. Không dùng `List`, `Optional` từ `typing`.
- Mảng NumPy được chú thích là `np.ndarray`. Ghi rõ kiểu phần tử trong docstring khi cần.

### 3.3 Comment và docstring (bắt buộc)

- Mỗi module có docstring đầu file: mục đích và cách dùng.
- Mỗi lớp và hàm công khai có docstring theo kiểu Google, gồm `Args`, `Returns`, `Raises` khi có. Viết bằng tiếng Việt.
- Comment giải thích **vì sao**, không lặp lại **cái gì** code đã nói. Đặc biệt ghi chú các trường hợp biên: chia cho 0, miền xác định của `log` và `sqrt`, hàm phân kỳ, điểm gián đoạn.
- Mọi hằng số đặc biệt (ngưỡng sai số, số mẫu) có comment một dòng.

Ví dụ:

```python
def sample(self, x_min: float, x_max: float, samples: int) -> tuple[np.ndarray, np.ndarray]:
    """Lấy mẫu hàm số trên khoảng ``[x_min, x_max]``.

    Args:
        x_min: Cận dưới của miền x.
        x_max: Cận trên của miền x, phải lớn hơn ``x_min``.
        samples: Số điểm lấy mẫu.

    Returns:
        Cặp mảng ``(x, y)``. Giá trị ``y`` không xác định (chia 0, ngoài miền
        xác định) được đặt thành ``NaN`` để đường vẽ bị ngắt thay vì nối sai.

    Raises:
        ValueError: Khi ``x_min >= x_max`` hoặc ``samples < 2``.
    """
```

### 3.4 Xử lý lỗi toán học

- Lỗi nhập liệu do người dùng gây ra được báo bằng `ExpressionError` (lớp con của `ValueError`) với thông báo tiếng Việt rõ ràng.
- Giá trị không xác định được biểu diễn bằng `NaN`, không ném ngoại lệ trong quá trình vẽ.
- Bọc các phép tính NumPy trong `np.errstate(all="ignore")` để tránh cảnh báo tràn số làm rối log.

### 3.5 Giao diện (Dark Mode)

- Nền tối, màu chữ sáng. Cấu hình theme trong `.streamlit/config.toml`.
- Mỗi đường đồ thị có một màu riêng lấy từ bảng `PALETTE` trong `graph_app/plotting.py`. Không hard-code màu ở nơi khác.

---

## 4. Cấu trúc thư mục chuẩn

```
Claude_Code_Prj01/
├── CLAUDE.md
├── README.md
├── app.py                    # Điểm vào Streamlit: đọc ô nhập, tự nhận diện 2D/3D, hiện badge
├── graph_app/
│   ├── __init__.py
│   ├── math_engine.py        # Phân tích biểu thức (1 hoặc 2 biến), lấy mẫu, tìm giao điểm 2D  [lõi, không Streamlit]
│   ├── plotting.py           # Dựng biểu đồ 2D Plotly theo Dark Mode                         [lõi, không Streamlit]
│   ├── surface.py            # Lưới np.meshgrid, mặt Z = f(x, y), đường giao hai mặt 3D        [lõi, không Streamlit]
│   ├── plotting_3d.py        # Dựng biểu đồ 3D Plotly (Surface, Scatter3d), bảng màu            [lõi, không Streamlit]
│   ├── equations.py          # Phân loại phương trình: explicit y = g(x) hoặc implicit F = A − B  [lõi, không Streamlit]
│   ├── implicit.py           # Đường ẩn 2D (contourpy), giao điểm ẩn (Newton), mặt ẩn 3D, đường giao 3D  [lõi, không Streamlit]
│   ├── ui_theme.py           # CSS Dark Mode: nền #0E1117, ô nhập, thanh chuyển chế độ          [Streamlit, UI/UX]
│   ├── ui_help.py            # Bảng Math Syntax Helper ở sidebar, hiển thị lỗi thân thiện        [Streamlit, UI/UX]
│   ├── ui_sidebar.py         # Ba ô nhập phương trình, phạm vi trục, bảng màu, cheatsheet       [Streamlit]
│   ├── ui_2d.py              # Vẽ đồ thị 2D (không có sidebar, không có ô nhập)                 [Streamlit]
│   └── ui_3d.py              # Cảnh 3D chung: mặt z = f(x, y), mặt ẩn, đường giao               [Streamlit]
├── tests/
│   ├── test_math_engine.py
│   ├── test_plotting.py
│   ├── test_surface.py
│   ├── test_plotting_3d.py
│   └── test_app.py
├── docs/
│   ├── SPEC.md
│   └── ARCHITECTURE.md
├── .streamlit/
│   └── config.toml
├── pytest.ini
├── requirements.txt          # Thư viện runtime, dùng cho Streamlit Cloud
├── requirements-dev.txt      # Runtime + pytest
└── .gitignore
```

Quy tắc phụ thuộc:

- `app.py` → `ui_2d` / `ui_3d` → các module lõi.
- `plotting` → `math_engine`. `plotting_3d` → `plotting` (chỉ lấy hằng số giao diện) và `surface`.
- `surface` → `math_engine`.
- Các module lõi (`math_engine`, `plotting`, `surface`, `plotting_3d`) **không được import Streamlit**. Giao diện chỉ nằm trong `ui_*.py` và `app.py`.
- Không có chiều ngược lại.

Quy tắc khi thêm tính năng mới:

- Tính năng 2D và 3D phải tách file. Sửa một chế độ không được đổi hành vi chế độ kia; test 2D cũ phải vẫn pass.
- Hàm dùng chung cho hai chế độ (như `parse_expression`) nhận tham số, không nhân đôi code.
- Mọi test UI thêm vào `tests/test_app.py` dùng `AppTest`, không mở trình duyệt.

---

## 5. Checklist Code Review (Reviewer)

- [ ] Có type hint đầy đủ, `python -m pytest` pass toàn bộ.
- [ ] Không có `eval`/`exec` trên đầu vào người dùng, không có `except:` trần.
- [ ] Mỗi hàm công khai có docstring tiếng Việt; comment giải thích vì sao.
- [ ] Các trường hợp biên (chia 0, log/căn ngoài miền, tan gián đoạn) được xử lý và có test.
- [ ] Màu đồ thị và nền lấy từ hằng số, giao diện đúng Dark Mode.
- [ ] `requirements.txt` ghi phiên bản cố định và không chứa `pytest`.
- [ ] `.gitignore` loại bỏ `venv/`, `__pycache__/`, `.pytest_cache/`, `.streamlit/secrets.toml`.
- [ ] `README.md` có hướng dẫn chạy local và deploy lên Streamlit Community Cloud.

---

## 6. Quy trình phiên bản 1.2 (phương trình ẩn, 7 Agents)

- Luồng bàn giao: Orchestrator → PO/BA → Architect → **UI/UX Specialist** → Lead Dev → QA → Reviewer/Deploy → Orchestrator nghiệm thu.
- UI/UX Specialist chốt bảng màu neon (`PALETTE` trong `plotting.py`), quy tắc đặt nhãn chống chồng chữ (`place_labels`), CSS trong `ui_theme.py`, và văn bản lỗi trong `ui_help.py` trước khi Lead Dev viết giao diện.
- Mọi lỗi nhập liệu phải có thông báo tiếng Việt kèm gợi ý sửa khi có thể (ví dụ `xy` → `x*y`, `x2` → `x^2`).
- Phương trình `A = B` luôn được biến đổi thành `A − B = 0` trước khi tính. Phương trình dạng `y = g(x)` giữ dạng explicit để đồ thị chính xác và nhanh hơn.
- Tính toán đường giao và điểm giao ẩn không được phụ thuộc Streamlit. Mọi kiểm thử số học nằm trong `tests/test_implicit.py` và `tests/test_equations.py`.

---

## 7. Quy trình phiên bản 1.3: tự động nhận diện (không còn nút chọn chế độ)

Lộ trình refactor (Orchestrator):

1. `graph_app/equations.py`: viết lại thành `parse_user_equation` và `parse_all_equations`. Mọi ô nhập đi qua đây. Không còn `parse_equation_2d` và `parse_equation_3d`.
2. `graph_app/ui_sidebar.py` (mới): ba ô nhập, khoảng trục x, y, z, bảng màu, khung y tự động, độ phân giải và cheatsheet. Ô nhập nằm ở sidebar.
3. `app.py`: không còn radio chọn chế độ. Đọc các ô nhập, nhận diện chiều, hiện badge, rồi gọi `ui_2d` hoặc `ui_3d`.
4. `graph_app/plotting_3d.py`: một hàm `build_scene_3d` vẽ đồng thời mặt `z = f(x, y)` và mặt ẩn.
5. Test: viết lại `test_equations.py` và `test_app.py`. Giữ nguyên `test_implicit.py` và `test_surface.py` nhưng cập nhật cách lấy hàm.

Quy tắc nhận diện chiều (chỉ dựa vào các biến xuất hiện trong ô nhập):

- Nếu có ít nhất một ô chứa `z`, cả hệ thống chuyển sang đồ thị 3D. Mọi phương trình được vẽ trong không gian 3D.
- Nếu không ô nào chứa `z`, hệ thống ở đồ thị 2D.
- Trong 3D, `y = g(x)` và đường ẩn 2D được vẽ thành mặt trụ đứng, vì đó là đúng hình học của chúng.
- Mọi lỗi nhập liệu phải chỉ rõ ô nào sai (`f1`, `f2` hoặc `f3`).

---

## 8. Quy trình phiên bản 1.4: tối ưu giao diện và giao điểm

Phân công (Orchestrator):

1. **Header một dòng:** tiêu đề bên trái, badge chế độ canh phải, hướng dẫn gom vào popover `(i)`. Xem `ui_theme.render_header`.
2. **Sidebar:** cheatsheet mở bằng hộp thoại (`ui_help.open_cheatsheet`). Phạm vi và màu sắc gom vào `st.expander`.
3. **Màu theo cặp giao:** mỗi cặp có một màu cố định, khai báo trong `plotting.PAIR_COLORS`. Màu chữ của thông báo phải trùng với màu trên đồ thị.
4. **Chế độ làm nổi bật:** `ui_focus.render_focus_controls` trả về tập cặp cần làm nổi bật, hoặc `None` khi tắt. Khi bật, các đường gốc và mặt gốc giảm độ mờ, còn cặp được chọn phóng to.
5. **Văn bản giao tuyến:** dạng `f1 ∩ f2: Biểu diễn qua phương trình giao tuyến: <hệ phương trình>`. Không ghi các cụm như "được tô sáng".

Quy tắc khi sửa giao diện: mọi màu khai báo một chỗ trong các module lõi (`plotting`, `plotting_3d`, `ui_theme`), không hard-code ở nơi khác.

---

## 9. Quy trình phiên bản 1.5: tinh chỉnh giao diện và luồng tương tác

1. **Header:** `block-container` có khoảng trên đủ lớn để không bị thanh Deploy của Streamlit che. Xem `ui_theme.DARK_CSS`.
2. **Sidebar:** đúng thứ tự: tiêu đề, mô tả, `f1`, `f2`, `f3`, nút hướng dẫn, expander cấu hình. Xem `ui_sidebar.render_sidebar`.
3. **Làm nổi bật:** bỏ công tắc chung. Mỗi cặp giao có một checkbox ngay dưới đồ thị, mặc định không tích. Xem `ui_focus.render_pair_rows`.
4. **Thứ tự hiển thị:** đồ thị nằm trong một `st.container` được tạo trước. Các checkbox được render sau, rồi đồ thị được điền vào container đó. Nhờ vậy đồ thị dùng đúng trạng thái checkbox của cùng lần chạy.

---

## 10. Quy trình phiên bản 1.6: nhập liệu động (2 đến 6 hàm)

- Danh sách ô nhập nằm trong `st.session_state` (`equation_slot_ids`). Mỗi ô có mã định danh ổn định, nên xóa một ô không làm mất nội dung các ô còn lại. Xem `ui_sidebar.py`.
- Giới hạn: `MIN_EQUATIONS = 2`, `MAX_EQUATIONS = 6`. Nút thêm và nút xóa bị vô hiệu hóa khi chạm giới hạn.
- Bảng màu: 6 màu cho đường cong (`PALETTE`), 15 màu cho 15 cặp (`PAIR_COLORS`, sinh từ `itertools.combinations`).
- Parser: `|x|` được đổi thành `abs(x)` trước khi kiểm tra ký tự (`math_engine._replace_abs_bars`). `pi`, `e` và `exp` hoạt động sẵn.
- Legend của biểu đồ 2D và 3D đều tắt. Thông tin giao điểm chỉ đi qua checkbox dưới đồ thị.

---

## 11. Kiểm thử giao diện tự động (phiên bản 1.7)

- Lệnh chạy: `python ui_test_agent.py`. Script khởi động Streamlit ở cổng 8510, mở Chromium headless bằng Playwright, nhập hàm 2D và 3D, bật làm nổi bật, rồi chụp sáu trạng thái (cả màn hình máy tính và điện thoại).
- Ảnh và báo cáo nằm trong `ui_artifacts/`, thư mục này không đưa lên Git.
- Kiểm tra tự động trên DOM: chồng chữ giữa các phần tử HTML, chồng nhãn chú thích trên đồ thị (đo khung chữ, không đo mũi tên), tràn chiều ngang, nền không tối, lỗi JavaScript.
- Đánh giá thị giác (vision review) được thực hiện bằng cách đọc các ảnh PNG. Script không gọi mô hình thị giác.
- Mốc chuẩn trên máy desktop 1440 px: vùng vẽ 924×494 px (đo bằng trình duyệt). `PLOT_SIZE_PX` trong `plotting.py` phải khớp với mốc này.
- Trên màn hình hẹp (dưới 640 px), nhãn chú thích bị ẩn bằng CSS, vì vùng vẽ không đủ chỗ. Tọa độ vẫn hiện trong danh sách bên dưới đồ thị.

---

## 12. Thanh legend phía trên biểu đồ (phiên bản 1.8)

- Mỗi hàm có một checkbox trên thanh ngang, đặt giữa header và đồ thị (`ui_legend.render_legend_bar`). Checkbox mặc định được tích. Dải màu và nhãn của mỗi hàm đều lấy màu từ `PALETTE`.
- Sidebar không còn checkbox nào cạnh ô nhập.
- Bỏ tích một hàm làm mờ (`DIM_OPACITY = 0.15`) đường hoặc mặt của hàm đó, cùng mọi cặp giao có liên quan. Việc này đi qua tham số `dimmed_names` của `build_figure` và `build_scene_3d`, với tên hàm lấy từ `plotting.function_name`.
- Checkbox legend gắn với `slot_id` ổn định, nên xóa một hàm không làm thay đổi trạng thái của các hàm khác.
- Checkbox của từng cặp giao vẫn nằm dưới biểu đồ, và hoạt động độc lập với legend.

---

## 13. Rà soát toán học (phiên bản 1.9)

Các điểm đã kiểm tra bằng số và đã sửa:

1. **Tiệm cận có khung chung cao.** Quy tắc cũ chỉ so bước nhảy với chiều cao khung chung, nên `tan(x)` vẽ cùng `x^5` vẫn có đường ma. Thêm quy tắc thứ hai trong `plotting.break_discontinuities`: điểm đổi dấu mà cả hai đầu đều lớn hơn `_ASYMPTOTE_FACTOR` (10) lần độ lớn trung vị của chính hàm thì là tiệm cận.
2. **Mặt ma ở biên miền xác định (3D).** Ô `NaN` từng được thay bằng số dương lớn, làm isosurface vẽ thêm một mặt tại biên. Đổi sang sao chép giá trị của ô hữu hạn gần nhất (`implicit._fill_nearest`), không tạo nghiệm mới.
3. **Nhãn `-0.0000`.** Tọa độ giao điểm hai biến gần 0 được làm tròn về 0 (`implicit._snap_zero`).
4. **Miền xác định.** Kiểm tra với `-W error`: không có cảnh báo tràn số hay căn/log ngoài miền. Ngoài miền trả về NaN.

Giới hạn đã biết, chưa sửa:

- Căn bậc lẻ của số âm, như `x^(1/3)` với `x < 0`, vẫn là NaN theo quy ước miền số thực.
- Giao điểm hai đường ẩn 2D không tìm được các điểm tiếp xúc (không đổi dấu). Đã sửa ở phiên bản 2.7 (mục 19).
- Đường giao 3D giữa hai mặt ẩn đã được chiếu về đúng đường giao từ phiên bản 2.8 (mục 20).

---

## 14. Danh mục hàm số nổi tiếng (phiên bản 2.0)

- `graph_app/presets.py` chứa 20 mẫu: 10 đường 2D và 10 mặt 3D. Dropdown "🏛️ Hàm số nổi tiếng (Presets)" nằm ở đầu sidebar.
- Chọn một mẫu sẽ điền công thức vào ô `f1` qua callback `_apply_preset`. Chiều được nhận diện tự động như khi gõ tay, các ô khác giữ nguyên.
- Mặt trụ dùng dạng `x**2 + y**2 = 9 + sin(z)**2 + cos(z)**2 - 1`. Đây là đồng nhất thức, nên tập nghiệm vẫn là hình trụ bán kính 3. Dạng này được chọn vì SymPy tự rút gọn `0*z`, `z - z` và các biến thể tương tự, khiến `z` biến mất và quy tắc tự nhận diện xếp mặt trụ vào 2D.
- `tests/test_presets.py` kiểm tra: đủ 20 mẫu, mỗi mẫu biên dịch không cảnh báo, đúng chiều của nhóm, có dữ liệu vẽ được, và hành vi dropdown.

---

## 15. Preset theo từng ô và trục 2D rõ ràng (phiên bản 2.1)

Phân công trong đợt này (các vai trò được thực hiện tuần tự trong cùng một phiên, không tạo agent con):

- **Orchestrator:** xác định hai yêu cầu, chọn thứ tự: trục 2D trước (ảnh hưởng toàn bộ biểu đồ), sau đó preset.
- **Product Owner:** mỗi ô nhập có dropdown mẫu riêng, đặt ngay dưới ô nhập. Chọn mẫu điền đúng ô đó, không ảnh hưởng ô khác.
- **UI/UX Specialist:** dropdown dùng nhãn ngắn, placeholder ở mục đầu. Trục x và y đều có đường trục rõ, tên trục, vạch chia.
- **Architect và Lead Developer:** nguyên nhân trục tung "biến mất" là màu `zerolinecolor` (`#4A4F5C`) quá tối trên nền `#0E1117`. Trục hoành có đường y = 0 sáng hơn nên còn thấy. Đã thêm `AXIS_LINE_COLOR = #8B949E`, `showline`, `ticks`, tên trục, và tăng lề trái/dưới (`l=64`, `b=56`) để chứa nhãn.
- **QA và Reviewer:** test theo từng ô (`preset_choice_{slot_id}`), test trục có `showline`, tiêu đề, và màu đường trục. Đã kiểm tra bằng ảnh chụp trình duyệt.

Quy tắc: mọi khóa widget preset có tiền tố `preset_choice_` và gắn với mã định danh ổn định của ô (`slot_id`), không gắn với vị trí.

- **Bố cục hàng nhập (cập nhật 2.2):** mỗi ô gồm ô nhập, icon mẫu nổi tiếng (popover chứa dropdown), rồi icon xóa. Dropdown không nằm dưới ô nữa. Xem `ui_sidebar._render_equation_row`.

- **Phạm vi trục bằng ô nhập số (cập nhật 2.3):** mỗi trục có hai `st.number_input` min và max thay cho thanh trượt. `ui_sidebar.axis_ranges_valid(state, dimension)` kiểm tra min < max. Trục z chỉ kiểm tra khi là 3D. Nếu sai, `app.py` báo lỗi và không vẽ.

---

## 16. Tính toán theo khung nhìn (phiên bản 2.4)

Giới hạn của Streamlit: `st.plotly_chart` chỉ phát sự kiện chọn (`points`, `box`, `lasso`). Không có sự kiện zoom hay pan, nên mã Python không chạy lại khi người dùng zoom trong trình duyệt. Không thể làm "tính lại khi thả chuột" nếu không có một thành phần tùy chỉnh (custom component) hai chiều gửi `relayoutData` về Python.

Cách đã triển khai (`graph_app/viewport.py`):

- Dữ liệu tính trên miền rộng gấp ba khung nhìn (`PADDING = 1.0` mỗi phía). Zoom out vẫn có nhánh đồ thị.
- Số điểm lấy mẫu tỉ lệ với độ rộng miền (`samples_for`), có giới hạn trên và dưới. Zoom in vào khoảng hẹp vẫn mịn.
- Giao điểm, bảng tọa độ và khung y tự động chỉ dùng phần trong khung nhìn.
- Cảnh 3D tính lưới trên miền mở rộng. Khung hiển thị là khoảng người dùng chọn.

Hạn chế đã biết:

- Nhãn chú thích được đặt theo khung nhìn lúc vẽ. Khi zoom trong trình duyệt, nhãn có thể chồng nhau.
- Giao điểm nằm ngoài khung nhìn không được vẽ, nên khi zoom out sẽ không thấy chúng.
- Mật độ lấy mẫu giảm khi zoom out rất xa, vì số điểm bị giới hạn trên.

---

## 17. Tìm giao điểm bằng giải phương trình (phiên bản 2.5)

Yêu cầu từ Product Manager: không tìm giao điểm trên mảng điểm vẽ đồ thị. Giao điểm được tìm bằng cách giải `g(x) = f1(x) - f2(x) = 0`. Ví dụ `x^2 + 4x - 15` và `x*sin(x)` trên `[-10, 10]` cho đúng 2 nghiệm.

Thuật toán (`math_engine.find_intersections`):

1. **Đa thức:** nếu `f1 - f2` là đa thức theo `x`, giải bằng SymPy (`Poly.nroots`, 30 chữ số). Bắt được mọi nghiệm kể cả nghiệm bội.
2. **Hàm khác (sin, exp, log, căn...):** chia khoảng thành `samples` đoạn con, tìm đoạn đổi dấu, giải đồng loạt từng đoạn bằng chia đôi trên NumPy (`_bisect_roots`). Cặp nghiệm nằm chung một ô lưới được bắt bằng đỉnh parabol và cực trị của `h`. Cực tiểu của `|h|` không đổi dấu được tối ưu hóa bằng `minimize_scalar` để bắt tiếp xúc.
3. **Kiểm tra:** mọi ứng viên đều được xác nhận lại bằng `|f1 - f2| <= 1e-9 * max(1, |f|, |g|)`, rồi gộp trùng. Nhờ đó tiệm cận của `1/x` không bị nhận nhầm.

Giới hạn đã biết:

- Nghiệm bội của đa thức chỉ chính xác tới cỡ √ε ≈ 1e-8, vì float64 không phân giải được δ² nhỏ hơn ε.
- Đoạn chứa điểm không xác định (NaN) bị bỏ qua. Hiếm khi làm mất nghiệm thật nằm sát điểm đó.
- Giao điểm của hai đường ẩn 2D dùng hai nhánh: giao cắt (lưới ô và Newton) và tiếp xúc (mục 19).
- Phụ thuộc mới: `scipy==1.17.1` trong `requirements.txt`.

Chỉnh sửa sau đó (kiểm tra trên trình duyệt):

- Khung x mặc định là `[-6, 6]` (`ui_sidebar.DEFAULT_XY_RANGE`). Từ phiên bản 2.6, khi `x_auto` bật, khung x được canh theo giao điểm, nên không cần chỉnh tay.
- Nhãn giao điểm không còn đè lên nhau. Khi không tìm được chỗ trống, nhãn bị ẩn (`place_labels` trả về `None`). Điểm vẫn được đánh dấu, và tọa độ vẫn hiện trong bảng "Điểm giao nhau" và khi rê chuột.

---

## 18. Thứ tự canh khung và trách nhiệm kiểm tra toán (phiên bản 2.6)

Quy tắc bắt buộc, do lỗi ở phiên bản 2.5 gây ra:

1. **Tính giao điểm trước, canh khung sau.** Không đặt khung x hay y (kể cả giá trị mặc định) trước khi biết giao điểm. Khung x tự canh (`x_auto`) được tính bằng `viewport.fit_view` từ bao của mọi giao điểm, có đệm và độ rộng tối thiểu. Khung y tự canh (`y_auto`) bao theo đồ thị và giao điểm. Khi y tự canh, không được lọc giao điểm theo khoảng y mặc định.
2. **Ngoại lệ:** khi người dùng tắt tự canh, khung là giá trị họ nhập và giao điểm ngoài khung bị ẩn.
3. **Vô số giao điểm** (hai hàm trùng nhau) không đưa vào việc canh khung. Hàm `find_intersections` trả về rỗng trong trường hợp này.
4. **Giới hạn đã biết:** giao điểm ngoài cửa sổ dò ±200 (`ui_2d.SEARCH_HALF_WIDTH`) không được tìm khi khung tự canh.

Trách nhiệm theo vai trò:

- **📐 Mathematician Consultant** phải duyệt mọi thay đổi về cách tìm nghiệm, miền dò, và quan hệ giữa khung và giao điểm, trước khi Lead Developer viết mã.
- **🧪 Tester** kiểm tra logic toán, không chỉ giao diện: mọi giao điểm trong miền dò phải nằm trong khung, và đối chiếu số nghiệm với một phương pháp độc lập (quét lưới mịn hoặc nghiệm đại số).
- **Nhãn chú thích** là bước cuối: chỉ đặt nhãn sau khi khung đã cố định. Nhãn không có chỗ trống thì ẩn, tọa độ vẫn ở bảng.

---

## 19. Tiếp xúc giữa đường ẩn 2D (phiên bản 2.7)

Lỗi đã có: nhánh giao cắt chỉ tìm điểm mà F và G đổi dấu trong cùng một ô lưới. Tại tiếp xúc, hai đường chạm nhau mà không đổi dấu, và gradient song song làm Jacobian suy biến. Kết quả là mọi tiếp xúc giữa đường ẩn và đường khác đều bị bỏ sót, kể cả x² + y² = 25 với y = 5.

Cách sửa (`implicit._tangent_solutions`):

1. Tìm cực tiểu địa phương của `F² + G²` đã chuẩn hóa theo độ lớn mỗi hàm, trên 8 lân cận. Chỉ giữ điểm có giá trị ≤ `_TANGENT_SCREEN_R` (0.05), tối đa `_TANGENT_MAX_STARTS` (400) điểm khởi đầu.
2. Tinh chỉnh từng điểm bằng `scipy.optimize.least_squares` (Levenberg–Marquardt) trên hệ `(F, G)`.
3. Chỉ nhận nghiệm nằm trong khung và có `|F|`, `|G|` ≤ `_RESIDUAL_RELATIVE` × độ lớn hàm.

Các ca đã kiểm tra (`tests/test_implicit.py::TestTangencyAdversarial`): tiếp xúc với đường thẳng ngang và chéo, parabol với tiếp tuyến, tiếp điểm lệch lưới, tiếp xúc ngoài và trong của hai đường tròn, cosine chạm đường thẳng tại nhiều điểm, nút và cusp qua gốc, tiếp điểm trùng điểm lưới, hai nghiệm cách nhau nhỏ hơn bước lưới, âm tính giả khi khoảng cách 0.001, hai đường trùng nhau.

Giới hạn đã biết:

- Nghiệm tiếp xúc chính xác đến khoảng √ε ≈ 1e-8. Tọa độ dưới 1e-6 được làm tròn về 0 (`implicit._snap_zero`) để nhãn không hiện "-0.0000".
- Nếu một cặp có hơn 400 điểm lưới cực tiểu ở mức sàng, một số tiếp xúc có thể bị bỏ sót.
- Tiếp xúc trong không gian 3D (mặt ẩn với mặt ẩn) chưa được xử lý; đường giao 3D vẫn là xấp xỉ theo voxel.
- Tiếp tuyến tại một điểm (tính năng dự kiến) sẽ dùng cùng gradient ∇F, nên nên tái sử dụng hàm tính đạo hàm khi triển khai.

Bộ ca đặc biệt cuối (`tests/test_special_cases.py`, 29 ca): nghiệm bội 4, sin x = sin 2x trên một chu kỳ, tiệm cận 1/x, miền √x và log, |x| = 2, song song, nghiệm ngoài khung, tia trùng nhau (không liệt kê vô số điểm), hai đường tròn, đường tròn với hypebol (bốn điểm), elip tiếp xúc, đồng tâm, nút và cusp, paraboloid với mặt phẳng, mặt phẳng với mặt phẳng, mặt tiếp xúc, mặt ẩn tiếp xúc và rời nhau. Đáp số tính tay từ công thức. Ca 3D xấp xỉ theo lưới nên kiểm tra từng điểm nằm trên cả hai mặt với dung sai theo bước lưới.

---

## 20. Đường giao 3D chính xác và điểm tiếp xúc 3D (phiên bản 2.8)

Module mới `graph_app/refine.py` (không dùng Streamlit):

- `project_points`: Gauss–Newton theo bình phương tối thiểu, Jacobian sai phân trung tâm, nghịch đảo giả nên chạy được khi Jacobian thiếu hạng.
- `isolated_tangencies`: điểm tiếp xúc giữa hai mặt ẩn, lấy cực tiểu của F² + G² (chuẩn hóa) trên 26 lân cận, tinh chỉnh bằng Gauss–Newton, kiểm tra phần dư và gộp điểm trùng.

Áp dụng:

- Mặt tường minh (`surface.intersection_curves`, tham số `func_b`): điểm đường mức được chiếu về `f₁ − f₂ = 0`, rồi z = f₁(x, y). Sai số đo được khoảng 1e−16 (trước đây là sai số nội suy cỡ bước²).
- Mặt ẩn (`implicit.implicit_surface_intersection`, tham số `refine_with`): đầu mút đoạn voxel được chiếu về `{F = 0, G = 0}`. Sai số đo được khoảng 1e−16.
- Điểm tiếp xúc 3D được vẽ như khối một điểm trong cùng trace, với marker kích thước `ISOLATED_MARKER_PX` (plotting_3d). Các điểm trên đường có marker kích thước 0.

Kiểm tra (`tests/test_special_cases.py`): paraboloid với mặt phẳng, mặt cầu với mặt phẳng và mặt cầu tiếp xúc hai điểm, tiếp xúc mặt cầu với mặt phẳng tại (0, 0, 1).

Giới hạn còn lại:

- Tiếp điểm chính xác đến √ε ≈ 1e−8 vì nghiệm kép. Đó là giới hạn của float64, không phải lỗi.
- Tiếp xúc giữa hai mặt tường minh 3D chưa được tìm dưới dạng điểm (chỉ có đường giao). Chỉ mặt ẩn có tiếp điểm.
- Điểm khởi đầu tiếp xúc giới hạn ở 2000 cực tiểu có F²+G² nhỏ nhất.
