"""Lõi toán cho phương trình ẩn ``F(x, y) = 0`` (2D) và ``F(x, y, z) = 0`` (3D).

Thuật toán:

- **Đường ẩn 2D:** lấy đường mức 0 của ``F`` trên lưới bằng ``contourpy``.
- **Giao điểm hai đường ẩn 2D:** trong mỗi ô lưới có cả ``F`` và ``G`` đổi dấu,
  giải hệ tuyến tính xấp xỉ bậc nhất để có điểm ứng viên, rồi tinh chỉnh bằng
  Newton trên hệ ``F = G = 0`` thật. Chỉ nhận điểm có phần dư đủ nhỏ.
- **Mặt ẩn 3D:** lưới ba chiều cho ``go.Isosurface``. Ô ``NaN`` (ngoài miền xác định)
  được thay bằng giá trị của ô hữu hạn gần nhất, để không tạo mặt ma ở biên miền.
- **Đường giao hai mặt ẩn 3D:** trong mỗi voxel có cả ``F`` và ``G`` đổi dấu, xấp xỉ
  hai mặt bằng mặt phẳng, lấy giao của hai mặt phẳng và cắt theo biên voxel.

Module này không phụ thuộc Streamlit.
"""

from __future__ import annotations

import numpy as np
from contourpy import contour_generator
from scipy.optimize import least_squares

from graph_app.math_engine import Intersection, ParsedFunction
from graph_app.refine import RESIDUAL_TOLERANCE, implicit_residuals, project_points, residual_norm_ok

GRID_2D: int = 300
"""Số điểm mỗi chiều của lưới 2D cho đường ẩn và giao điểm ẩn."""

GRID_3D_DEFAULT: int = 35
"""Số điểm mỗi chiều của lưới 3D mặc định. Lưới 35³ khoảng 43 nghìn điểm cho mỗi mặt."""

GRID_3D_MAX: int = 60
"""Giới hạn số điểm mỗi chiều. Vượt mức này, dữ liệu gửi lên trình duyệt quá lớn."""

_NEWTON_ITERATIONS: int = 40
_FD_STEP: float = 1e-6
"""Bước sai phân hữu hạn để xấp xỉ đạo hàm riêng khi chạy Newton."""

_RESIDUAL_RELATIVE: float = 1e-7
"""Phần dư tương đối tối đa để một điểm được nhận là nghiệm của hệ ``F = G = 0``."""

_DEGENERATE_EPS: float = 1e-14
_TANGENT_SCREEN_R: float = 0.05
"""Chỉ thử tinh chỉnh tiếp xúc tại điểm lưới mà F² + G² (đã chuẩn hóa) nhỏ hơn mức này."""
_TANGENT_MAX_STARTS: int = 400
"""Số điểm khởi đầu tối đa cho tinh chỉnh tiếp xúc, để chi phí không tăng theo độ mịn lưới."""
"""Ngưỡng định thức để coi một hệ tuyến tính là suy biến."""


def implicit_curve_polylines(
    func: ParsedFunction,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    samples: int = GRID_2D,
) -> list[np.ndarray]:
    """Lấy các đường mức 0 của ``F(x, y)`` trong khung chữ nhật cho trước.

    Args:
        func: Hàm hai biến ``F``. Nghiệm là tập ``F = 0``.
        x_range: Khoảng x ``(x_min, x_max)``.
        y_range: Khoảng y ``(y_min, y_max)``.
        samples: Số điểm mỗi chiều của lưới.

    Returns:
        Danh sách các đường, mỗi đường là mảng ``(n, 2)`` gồm các cột x, y đã sắp thứ tự.
        Rỗng nếu ``F`` không đổi dấu trong khung.

    Raises:
        ValueError: Khi khoảng rỗng hoặc đảo ngược.
    """
    xs, ys = _axes(x_range, y_range, samples)
    values = func(*np.meshgrid(xs, ys))
    if not np.isfinite(values).any():
        return []
    generator = contour_generator(xs, ys, values)
    return [line for line in generator.lines(0.0) if len(line) >= 2]


def find_implicit_intersections(
    f: ParsedFunction,
    g: ParsedFunction,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    samples: int = GRID_2D,
) -> list[Intersection]:
    """Tìm điểm chung của hai đường ẩn ``F = 0`` và ``G = 0`` trong khung cho trước.

    Args:
        f: Phương trình thứ nhất ở dạng ẩn, ``variables == ("x", "y")``.
        g: Phương trình thứ hai ở dạng ẩn, ``variables == ("x", "y")``.
        x_range: Khoảng x của lưới tìm kiếm.
        y_range: Khoảng y của lưới tìm kiếm.
        samples: Số điểm mỗi chiều của lưới.

    Returns:
        Danh sách giao điểm đã sắp xếp theo x, đã loại trùng lặp. Tung độ là y của điểm.
        Rỗng nếu hai đường trùng nhau hoàn toàn, vì khi đó giao là cả một đường.

    Raises:
        ValueError: Khi khoảng rỗng hoặc đảo ngược.
    """
    xs, ys = _axes(x_range, y_range, samples)
    grid_x, grid_y = np.meshgrid(xs, ys)
    fv = f(grid_x, grid_y)
    gv = g(grid_x, grid_y)

    diff = fv - gv
    finite_diff = np.abs(diff[np.isfinite(diff)])
    scale = max(1.0, float(np.max(finite_diff, initial=0.0)))
    if finite_diff.size and float(np.max(finite_diff)) <= _DEGENERATE_EPS * scale:
        return []

    # Nhánh 1: giao cắt thông thường, tức có ô lưới mà cả F và G đổi dấu.
    cell_x, cell_y = _crossing_solutions(f, g, xs, ys, fv, gv)
    # Nhánh 2: tiếp xúc. Tại đó hai gradient song song nên nhánh 1 không hội tụ, cần cách khác.
    touch_x, touch_y = _tangent_solutions(f, g, xs, ys, fv, gv)
    return _deduplicate_points(
        np.concatenate([cell_x, touch_x]),
        np.concatenate([cell_y, touch_y]),
        xs,
        ys,
    )


def _crossing_solutions(
    f: ParsedFunction,
    g: ParsedFunction,
    xs: np.ndarray,
    ys: np.ndarray,
    fv: np.ndarray,
    gv: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Nghiệm giao cắt: nghiệm tuyến tính trong các ô có cả F và G đổi dấu, rồi Newton và kiểm tra phần dư.

    Args:
        f: Phương trình thứ nhất ở dạng ẩn.
        g: Phương trình thứ hai ở dạng ẩn.
        xs: Vector x của lưới.
        ys: Vector y của lưới.
        fv: Giá trị F trên lưới.
        gv: Giá trị G trên lưới.

    Returns:
        Cặp mảng ``(x, y)`` các nghiệm đã qua kiểm tra phần dư. Rỗng nếu không có ô nào.
    """
    cells = _cells_with_both_signs(fv, gv)
    if not cells[0].size:
        return np.empty(0), np.empty(0)
    cx, cy = _linear_cell_solutions(fv, gv, xs, ys, cells)
    if cx.size == 0:
        return np.empty(0), np.empty(0)
    nx, ny = _newton_system(f, g, cx, cy, step_limit=max(xs[1] - xs[0], ys[1] - ys[0]))
    tolerance = _RESIDUAL_RELATIVE * max(1.0, _max_finite(fv), _max_finite(gv))
    inside = (nx >= xs[0]) & (nx <= xs[-1]) & (ny >= ys[0]) & (ny <= ys[-1])
    ok = inside & (np.abs(f(nx, ny)) <= tolerance) & (np.abs(g(nx, ny)) <= tolerance)
    return nx[ok], ny[ok]


def _tangent_solutions(
    f: ParsedFunction,
    g: ParsedFunction,
    xs: np.ndarray,
    ys: np.ndarray,
    fv: np.ndarray,
    gv: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Nghiệm tiếp xúc: hai đường chạm nhau mà không đổi dấu, nên không có ô lưới đổi dấu.

    Cực tiểu địa phương của ``F² + G²`` (đã chuẩn hóa theo độ lớn của mỗi hàm) được dùng làm điểm
    khởi đầu. Từ đó tinh chỉnh bằng bình phương tối thiểu Levenberg–Marquardt, vì ở tiếp xúc
    Jacobian suy biến và Newton tuyến tính không hội tụ. Chỉ nhận nghiệm có phần dư nhỏ và nằm trong lưới.

    Args:
        f: Phương trình thứ nhất ở dạng ẩn.
        g: Phương trình thứ hai ở dạng ẩn.
        xs: Vector x của lưới.
        ys: Vector y của lưới.
        fv: Giá trị F trên lưới.
        gv: Giá trị G trên lưới.

    Returns:
        Cặp mảng ``(x, y)`` các nghiệm tiếp xúc. Có thể chứa nghiệm trùng, sẽ được gộp sau.
    """
    scale_f = _max_finite(fv)
    scale_g = _max_finite(gv)
    if scale_f <= 0.0 or scale_g <= 0.0:
        return np.empty(0), np.empty(0)
    with np.errstate(invalid="ignore"):
        merit = (fv / scale_f) ** 2 + (gv / scale_g) ** 2
    merit = np.where(np.isfinite(merit), merit, np.inf)

    # Cực tiểu địa phương trên 8 lân cận: so với mọi lân cận, kể cả đường chéo.
    padded = np.pad(merit, 1, constant_values=np.inf)
    is_min = np.ones(merit.shape, dtype=bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            neighbour = padded[1 + di : 1 + di + merit.shape[0], 1 + dj : 1 + dj + merit.shape[1]]
            is_min &= merit <= neighbour
    is_min &= merit <= _TANGENT_SCREEN_R

    rows, cols = np.nonzero(is_min)
    order = np.argsort(merit[rows, cols])[:_TANGENT_MAX_STARTS]
    tol_f = _RESIDUAL_RELATIVE * max(1.0, scale_f)
    tol_g = _RESIDUAL_RELATIVE * max(1.0, scale_g)
    found_x: list[float] = []
    found_y: list[float] = []
    for k in order:
        start = np.array([xs[cols[k]], ys[rows[k]]], dtype=float)
        result = least_squares(
            lambda p: np.array([float(f(p[0], p[1])), float(g(p[0], p[1]))]),
            start,
            method="lm",
            xtol=1e-15,
            ftol=1e-15,
            gtol=1e-15,
        )
        x, y = float(result.x[0]), float(result.x[1])
        inside = xs[0] <= x <= xs[-1] and ys[0] <= y <= ys[-1]
        if inside and abs(float(f(x, y))) <= tol_f and abs(float(g(x, y))) <= tol_g:
            found_x.append(x)
            found_y.append(y)
    return np.array(found_x), np.array(found_y)


def isosurface_grid(
    func: ParsedFunction,
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
) -> np.ndarray:
    """Tính ``F(x, y, z)`` trên lưới 3D, dùng cho ``go.Isosurface`` và tìm đường giao.

    Args:
        func: Hàm ba biến ``F``, ``variables == ("x", "y", "z")``.
        xs: Vector x của lưới.
        ys: Vector y của lưới.
        zs: Vector z của lưới.

    Returns:
        Mảng ``(len(xs), len(ys), len(zs))``, chỉ số theo thứ tự ``(i, j, k)`` ứng với ``(x, y, z)``.
        Điểm ``NaN`` được thay bằng giá trị của ô hữu hạn gần nhất.
    """
    grid_x, grid_y, grid_z = np.meshgrid(xs, ys, zs, indexing="ij")
    values = func(grid_x, grid_y, grid_z)
    return _fill_nearest(values)


def _fill_nearest(values: np.ndarray) -> np.ndarray:
    """Thay ``NaN`` bằng giá trị của ô hữu hạn gần nhất theo sáu hướng lân cận.

    Không dùng một số lớn cố định: số đó tạo ra một điểm đổi dấu giả ở biên miền xác định,
    và isosurface vẽ thành một mặt ma. Sao chép giá trị lân cận giữ nguyên dấu,
    nên không tạo nghiệm mới.

    Args:
        values: Lưới ba chiều có thể chứa ``NaN``.

    Returns:
        Lưới cùng kích thước, không còn ``NaN`` nếu lưới có ít nhất một giá trị hữu hạn.
    """
    filled = values.copy()
    missing = ~np.isfinite(filled)
    if not missing.any() or missing.all():
        return np.where(missing, 0.0, filled)
    while missing.any():
        progressed = False
        for axis in range(3):
            for shift in (1, -1):
                neighbour = np.roll(filled, shift, axis=axis)
                neighbour_ok = np.roll(~missing, shift, axis=axis)
                # np.roll bọc vòng qua biên; loại bỏ các lát bị bọc để không lấy giá trị sai.
                edge = [slice(None)] * 3
                edge[axis] = slice(0, 1) if shift == 1 else slice(-1, None)
                neighbour_ok[tuple(edge)] = False
                take = missing & neighbour_ok
                if take.any():
                    filled[take] = neighbour[take]
                    missing &= ~take
                    progressed = True
        if not progressed:
            break
    return filled


def implicit_surface_intersection(
    values_f: np.ndarray,
    values_g: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    refine_with: tuple[ParsedFunction, ParsedFunction] | None = None,
) -> np.ndarray:
    """Xấp xỉ đường giao của hai mặt ẩn ``F = 0`` và ``G = 0`` trên lưới 3D.

    Nếu truyền ``refine_with``, mỗi đầu mút được chiếu về đúng đường giao bằng Gauss–Newton
    (``graph_app.refine``). Đầu mút không hội tụ hoặc trôi quá hai voxel thì giữ nguyên.

    Args:
        values_f: Giá trị ``F`` trên lưới, từ ``isosurface_grid``.
        values_g: Giá trị ``G`` trên lưới, cùng kích thước với ``values_f``.
        xs: Vector x của lưới, đều.
        ys: Vector y của lưới, đều.
        zs: Vector z của lưới, đều.
        refine_with: Cặp ``(F, G)`` dạng hàm đã phân tích, để tinh chỉnh đầu mút. ``None`` để giữ xấp xỉ lưới.

    Returns:
        Mảng ``(k, 2, 3)``: mỗi phần tử là một đoạn thẳng ``[điểm đầu, điểm cuối]``
        trong tọa độ thế giới. Rỗng nếu hai mặt không cắt nhau trong lưới.
    """
    if values_f.shape != values_g.shape:
        raise ValueError("Hai lưới giá trị phải cùng kích thước.")
    if values_f.shape[0] < 2 or values_f.shape[1] < 2 or values_f.shape[2] < 2:
        return np.empty((0, 2, 3))

    corner_f = _voxel_corners(values_f)
    corner_g = _voxel_corners(values_g)
    active = _active_voxels(corner_f) & _active_voxels(corner_g)
    if not active.any():
        return np.empty((0, 2, 3))

    local = _unit_cube_corners()
    design_pinv = np.linalg.pinv(np.column_stack([local, np.ones(8)]))  # (4, 8)
    fa = corner_f[:, active].T  # (N, 8)
    ga = corner_g[:, active].T
    coef_f = fa @ design_pinv.T  # (N, 4): a_F · p + b_F ≈ F
    coef_g = ga @ design_pinv.T

    normals = np.stack([coef_f[:, :3], coef_g[:, :3]], axis=1)  # (N, 2, 3)
    offsets = np.stack([coef_f[:, 3], coef_g[:, 3]], axis=1)  # (N, 2)
    directions = np.cross(normals[:, 0], normals[:, 1])  # (N, 3)
    line_ok = np.linalg.norm(directions, axis=1) > _DEGENERATE_EPS
    if not line_ok.any():
        return np.empty((0, 2, 3))

    points = np.einsum("nij,nj->ni", np.linalg.pinv(normals), -offsets)  # (N, 3) điểm gần nhất gốc trên giao
    segments_local, kept = _clip_lines_to_unit_cube(points[line_ok], directions[line_ok])
    if segments_local.size == 0:
        return np.empty((0, 2, 3))

    # Chỉ số voxel phải đi cùng đúng các đường còn lại sau khi cắt, theo cùng thứ tự.
    voxel_index = np.argwhere(active)[line_ok][kept]
    origin = np.column_stack([xs[voxel_index[:, 0]], ys[voxel_index[:, 1]], zs[voxel_index[:, 2]]])
    spacing = np.array([xs[1] - xs[0], ys[1] - ys[0], zs[1] - zs[0]])
    segments_world = origin[:, None, :] + segments_local * spacing
    segments = segments_world[np.isfinite(segments_world).all(axis=(1, 2))]
    if refine_with is None or segments.size == 0:
        return segments
    return _refine_segments(segments, refine_with, spacing)


def _refine_segments(
    segments: np.ndarray,
    funcs: tuple[ParsedFunction, ParsedFunction],
    spacing: np.ndarray,
) -> np.ndarray:
    """Chiếu các đầu mút đoạn về đường giao ``{F = 0, G = 0}``, giữ nguyên điểm nào không hội tụ.

    Args:
        segments: Các đoạn ``(k, 2, 3)`` trong tọa độ thế giới.
        funcs: Cặp hàm ``(F, G)``.
        spacing: Bước lưới theo ba trục, để giới hạn độ trôi cho phép.

    Returns:
        Mảng ``(k, 2, 3)`` các đoạn đã chiếu.
    """
    residuals = implicit_residuals(funcs[0], funcs[1])
    ends = segments.reshape(-1, 3)
    moved = project_points(residuals, ends)
    max_move = 2.0 * float(np.linalg.norm(spacing))
    tolerance = np.full(2, RESIDUAL_TOLERANCE)
    ok = (
        np.isfinite(moved).all(axis=1)
        & (np.linalg.norm(moved - ends, axis=1) <= max_move)
        & residual_norm_ok(residuals, np.where(np.isfinite(moved), moved, ends), tolerance)
    )
    refined = np.where(ok[:, None], moved, ends)
    return refined.reshape(-1, 2, 3)


def _axes(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    samples: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Tạo hai vector lưới sau khi kiểm tra khoảng.

    Raises:
        ValueError: Khi khoảng rỗng hoặc đảo ngược, hoặc ``samples < 3``.
    """
    if x_range[0] >= x_range[1] or y_range[0] >= y_range[1]:
        raise ValueError("Cận dưới phải nhỏ hơn cận trên.")
    if samples < 3:
        raise ValueError("Lưới cần ít nhất 3 điểm mỗi chiều.")
    return np.linspace(*x_range, samples), np.linspace(*y_range, samples)


def _max_finite(values: np.ndarray) -> float:
    """Giá trị tuyệt đối lớn nhất trong các phần tử hữu hạn, hoặc 0 nếu không có."""
    finite = np.abs(values[np.isfinite(values)])
    return float(np.max(finite, initial=0.0))


def _cells_with_both_signs(fv: np.ndarray, gv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Tìm các ô lưới 2D mà cả ``F`` và ``G`` đổi dấu trên bốn đỉnh.

    Returns:
        Cặp chỉ số ``(rows, cols)`` của góc dưới-trái mỗi ô được chọn.
    """
    def corners(v: np.ndarray) -> np.ndarray:
        """Xếp bốn đỉnh của mọi ô thành mảng ``(4, ny-1, nx-1)``."""
        return np.stack([v[:-1, :-1], v[:-1, 1:], v[1:, :-1], v[1:, 1:]])

    cf = corners(fv)
    cg = corners(gv)
    finite = np.isfinite(cf).all(axis=0) & np.isfinite(cg).all(axis=0)
    both = (
        (cf.min(axis=0) <= 0) & (cf.max(axis=0) >= 0)
        & (cg.min(axis=0) <= 0) & (cg.max(axis=0) >= 0)
    )
    return np.nonzero(finite & both)


def _linear_cell_solutions(
    fv: np.ndarray,
    gv: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
    cells: tuple[np.ndarray, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Giải hệ hai phương trình tuyến tính xấp xỉ ``F`` và ``G`` trong mỗi ô.

    Mỗi hàm được xấp xỉ bằng mặt phẳng ``a + b·u + c·v`` qua bốn đỉnh ô, với ``(u, v) ∈ [0, 1]²``.
    Điểm giao của hai mặt phẳng là điểm ứng viên, chỉ giữ nếu nằm trong ô (có dung sai).

    Returns:
        Hai mảng tọa độ ``(x, y)`` của điểm ứng viên.
    """
    rows, cols = cells
    # Thứ tự đỉnh khớp với _cells_with_both_signs: (0,0), (1,0), (0,1), (1,1) theo (u, v).
    design = np.array([[1, 0, 0], [1, 1, 0], [1, 0, 1], [1, 1, 1]], dtype=float)
    pinv = np.linalg.pinv(design)  # (3, 4)

    def plane(v: np.ndarray) -> np.ndarray:
        """Hệ số ``(a, b, c)`` của mặt phẳng xấp xỉ cho từng ô được chọn, dạng ``(3, N)``."""
        corners = np.stack([
            v[rows, cols],
            v[rows, cols + 1],
            v[rows + 1, cols],
            v[rows + 1, cols + 1],
        ])
        return pinv @ corners

    pf = plane(fv)
    pg = plane(gv)
    # Hệ: b_F·u + c_F·v = -a_F ; b_G·u + c_G·v = -a_G
    det = pf[1] * pg[2] - pf[2] * pg[1]
    solvable = np.abs(det) > _DEGENERATE_EPS
    with np.errstate(divide="ignore", invalid="ignore"):
        u = (-pf[0] * pg[2] + pf[2] * pg[0]) / det
        v = (-pf[1] * pg[0] + pf[0] * pg[1]) / det
    margin = 1e-6
    inside = solvable & (u >= -margin) & (u <= 1 + margin) & (v >= -margin) & (v <= 1 + margin)
    dx = xs[1] - xs[0]
    dy = ys[1] - ys[0]
    cx = xs[cols[inside]] + u[inside] * dx
    cy = ys[rows[inside]] + v[inside] * dy
    return cx, cy


def _newton_system(
    f: ParsedFunction,
    g: ParsedFunction,
    x0: np.ndarray,
    y0: np.ndarray,
    step_limit: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Tinh chỉnh nghiệm của hệ ``F = G = 0`` bằng Newton, chạy song song trên mọi điểm.

    Args:
        f: Phương trình thứ nhất.
        g: Phương trình thứ hai.
        x0: Hoành độ điểm khởi đầu.
        y0: Tung độ điểm khởi đầu.
        step_limit: Độ dài bước tối đa mỗi vòng, tránh nhảy ra khỏi ô.

    Returns:
        Hoành độ và tung độ sau tinh chỉnh. Điểm suy biến giữ nguyên vị trí.
    """
    x = x0.astype(float).copy()
    y = y0.astype(float).copy()
    h = _FD_STEP
    with np.errstate(all="ignore"):
        for _ in range(_NEWTON_ITERATIONS):
            f0 = f(x, y)
            g0 = g(x, y)
            fx = (f(x + h, y) - f(x - h, y)) / (2 * h)
            fy = (f(x, y + h) - f(x, y - h)) / (2 * h)
            gx = (g(x + h, y) - g(x - h, y)) / (2 * h)
            gy = (g(x, y + h) - g(x, y - h)) / (2 * h)
            det = fx * gy - fy * gx
            valid = np.isfinite(det) & (np.abs(det) > _DEGENERATE_EPS) & np.isfinite(f0) & np.isfinite(g0)
            dx = np.where(valid, -(gy * f0 - fy * g0) / det, 0.0)
            dy = np.where(valid, (gx * f0 - fx * g0) / det, 0.0)
            dx = np.clip(dx, -step_limit, step_limit)
            dy = np.clip(dy, -step_limit, step_limit)
            x = x + dx
            y = y + dy
    return x, y


def _deduplicate_points(
    x: np.ndarray,
    y: np.ndarray,
    xs: np.ndarray,
    ys: np.ndarray,
) -> list[Intersection]:
    """Gộp các điểm trùng nhau trong phạm vi một ô lưới và sắp xếp kết quả.

    Args:
        x: Hoành độ các điểm ứng viên đã tinh chỉnh.
        y: Tung độ các điểm ứng viên.
        xs: Vector x của lưới, dùng để xác định kích thước ô.
        ys: Vector y của lưới.

    Returns:
        Danh sách ``Intersection`` đã sắp xếp theo ``(x, y)``.
    """
    if x.size == 0:
        return []
    tol_x = 0.5 * (xs[1] - xs[0])
    tol_y = 0.5 * (ys[1] - ys[0])
    order = np.lexsort((y, x))
    kept: list[tuple[float, float]] = []
    for idx in order:
        px, py = float(x[idx]), float(y[idx])
        if any(abs(px - qx) <= tol_x and abs(py - qy) <= tol_y for qx, qy in kept):
            continue
        kept.append((px, py))
    # Sai số Newton có thể cho -3e-17 thay vì 0. Làm tròn để nhãn không hiện "-0.0000".
    return [Intersection(x=_snap_zero(px), y=_snap_zero(py)) for px, py in kept]


def _snap_zero(value: float) -> float:
    """Đưa các giá trị gần 0 về đúng 0, tránh hiển thị "-0.0000" trên nhãn.

    Ngưỡng 1e-6 nhỏ hơn độ phân giải hiển thị 1e-4, nên không làm sai nhãn. Nghiệm tiếp xúc chỉ
    chính xác đến khoảng √ε ≈ 1e-8, nên ngưỡng 1e-10 cũ không đủ để bắt các giá trị như -2e-9.
    """
    return 0.0 if abs(value) < 1e-6 else value


def _voxel_corners(values: np.ndarray) -> np.ndarray:
    """Lấy giá trị tại tám đỉnh của mỗi voxel, theo thứ tự khớp với ``_unit_cube_corners``.

    Returns:
        Mảng ``(8, nx-1, ny-1, nz-1)``.
    """
    nx, ny, nz = values.shape
    out = np.empty((8, nx - 1, ny - 1, nz - 1))
    for idx, (di, dj, dk) in enumerate(_CORNER_OFFSETS):
        out[idx] = values[di : di + nx - 1, dj : dj + ny - 1, dk : dk + nz - 1]
    return out


def _active_voxels(corners: np.ndarray) -> np.ndarray:
    """Voxel có giá trị đổi dấu (hoặc chạm 0) trên tám đỉnh, và không có ``NaN``."""
    return (corners.min(axis=0) <= 0) & (corners.max(axis=0) >= 0)


def _unit_cube_corners() -> np.ndarray:
    """Tọa độ cục bộ ``(u, v, w)`` của tám đỉnh khối lập phương đơn vị, dạng ``(8, 3)``."""
    return np.array(_CORNER_OFFSETS, dtype=float)


def _clip_lines_to_unit_cube(points: np.ndarray, directions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Cắt các đường thẳng ``p + t·d`` theo khối lập phương đơn vị ``[0, 1]³``.

    Args:
        points: Điểm trên mỗi đường, dạng ``(N, 3)``.
        directions: Vector chỉ phương, dạng ``(N, 3)``, khác 0.

    Returns:
        Cặp ``(segments, kept)``. ``segments`` là mảng ``(M, 2, 3)`` gồm hai đầu đoạn
        thẳng nằm trong khối. ``kept`` là mặt nạ ``(N,)`` cho biết đường nào còn lại.
    """
    norms = np.linalg.norm(directions, axis=1, keepdims=True)
    d = directions / norms
    t_lo = np.full(len(points), -np.inf)
    t_hi = np.full(len(points), np.inf)
    parallel_outside = np.zeros(len(points), dtype=bool)
    for axis in range(3):
        component = d[:, axis]
        moving = np.abs(component) > 1e-12
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (0.0 - points[:, axis]) / component
            t2 = (1.0 - points[:, axis]) / component
        lo = np.minimum(t1, t2)
        hi = np.maximum(t1, t2)
        t_lo = np.where(moving, np.maximum(t_lo, lo), t_lo)
        t_hi = np.where(moving, np.minimum(t_hi, hi), t_hi)
        parallel_outside |= ~moving & ((points[:, axis] < 0) | (points[:, axis] > 1))
    valid = (~parallel_outside) & np.isfinite(t_lo) & np.isfinite(t_hi) & (t_hi > t_lo)
    start = points[valid] + t_lo[valid, None] * d[valid]
    end = points[valid] + t_hi[valid, None] * d[valid]
    return np.stack([start, end], axis=1), valid


_CORNER_OFFSETS: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (1, 0, 0),
    (0, 1, 0),
    (1, 1, 0),
    (0, 0, 1),
    (1, 0, 1),
    (0, 1, 1),
    (1, 1, 1),
)
"""Độ lệch chỉ số của tám đỉnh voxel. Thứ tự này dùng chung cho mọi hàm xử lý voxel."""
