"""Tinh chỉnh nghiệm 3D bằng Gauss–Newton, và tìm điểm tiếp xúc giữa hai mặt ẩn.

Lưới chỉ cho xấp xỉ: đường giao lấy từ voxel hoặc đường mức có sai số cỡ bước lưới. Module này
đưa mỗi điểm về đúng tập nghiệm ``{F = 0, G = 0}`` (hoặc ``{h = 0}`` với mặt tường minh) bằng
bình phương tối thiểu có Jacobian sai phân trung tâm. Điểm tiếp xúc là nghiệm suy biến mà lưới
không bắt được, nên được tìm từ cực tiểu của ``F² + G²`` rồi tinh chỉnh tương tự.

Module không phụ thuộc Streamlit.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import product

import numpy as np

from graph_app.math_engine import ParsedFunction

PROJECTION_STEPS: int = 60
"""Số vòng Gauss–Newton tối đa. Tại tiếp xúc hội tụ chậm (Jacobian suy biến), nên cần nhiều vòng."""

JACOBIAN_STEP: float = 1e-7
"""Bước sai phân trung tâm, tương đối với độ lớn tọa độ. Đủ nhỏ để sai số cắt cụt không lớn."""

RESIDUAL_TOLERANCE: float = 1e-9
"""Ngưỡng phần dư để coi một điểm là nghiệm, theo đơn vị giá trị hàm và nhân với độ lớn tham chiếu."""

TANGENT_SCREEN: float = 0.05
"""Chỉ thử tiếp xúc tại điểm lưới mà ``F² + G²`` chuẩn hóa nhỏ hơn mức này."""

TANGENT_MAX_STARTS: int = 2000
"""Số điểm khởi đầu tối đa cho tìm tiếp xúc 3D, để chi phí không tăng theo độ mịn lưới."""


def project_points(
    residuals: Callable[[np.ndarray], np.ndarray],
    points: np.ndarray,
    steps: int = PROJECTION_STEPS,
) -> np.ndarray:
    """Đưa các điểm về gần tập nghiệm ``residuals(p) = 0`` bằng Gauss–Newton theo bình phương tối thiểu.

    Bước dùng nghịch đảo giả (min-norm) của Jacobian, nên vẫn chạy được khi Jacobian thiếu hạng,
    ví dụ tại tiếp xúc. Bước không hữu hạn bị bỏ, điểm giữ nguyên.

    Args:
        residuals: Hàm nhận mảng ``(N, d)``, trả về mảng ``(N, m)`` phần dư.
        points: Các điểm khởi đầu ``(N, d)``.
        steps: Số vòng lặp tối đa.

    Returns:
        Mảng ``(N, d)`` các điểm đã tinh chỉnh. Có thể trôi xa nếu khởi đầu tồi; người gọi kiểm tra lại.
    """
    current = np.asarray(points, dtype=float).copy()
    for _ in range(steps):
        values = residuals(current)
        jacobian = _jacobian(residuals, current)
        step = np.einsum("nij,nj->ni", np.linalg.pinv(jacobian), -values)
        current = current + np.where(np.isfinite(step), step, 0.0)
    return current


def residual_norm_ok(
    residuals: Callable[[np.ndarray], np.ndarray],
    points: np.ndarray,
    tolerance: np.ndarray,
) -> np.ndarray:
    """Mặt nạ các điểm có mọi phần dư nhỏ hơn ngưỡng tương ứng.

    Args:
        residuals: Hàm phần dư, như trong ``project_points``.
        points: Các điểm cần kiểm tra ``(N, d)``.
        tolerance: Ngưỡng cho từng phần dư, dạng vector độ dài ``m``.

    Returns:
        Mảng bool độ dài ``N``. Điểm có phần dư ``NaN`` bị coi là không đạt.
    """
    values = residuals(points)
    with np.errstate(invalid="ignore"):
        return np.all(np.abs(values) <= tolerance, axis=1)


def implicit_residuals(f: ParsedFunction, g: ParsedFunction) -> Callable[[np.ndarray], np.ndarray]:
    """Phần dư ``(F, G)`` của hai mặt ẩn 3D, nhận mảng điểm ``(N, 3)``.

    Args:
        f: Phương trình ẩn thứ nhất, ``variables == ("x", "y", "z")``.
        g: Phương trình ẩn thứ hai, cùng dạng.

    Returns:
        Hàm trả về mảng ``(N, 2)``.
    """

    def residuals(points: np.ndarray) -> np.ndarray:
        """Cặp ``(F, G)`` tại từng điểm."""
        return np.column_stack([f(points[:, 0], points[:, 1], points[:, 2]), g(points[:, 0], points[:, 1], points[:, 2])])

    return residuals


def _jacobian(residuals: Callable[[np.ndarray], np.ndarray], points: np.ndarray) -> np.ndarray:
    """Jacobian ``(N, m, d)`` bằng sai phân trung tâm theo từng biến."""
    columns = []
    for k in range(points.shape[1]):
        step = JACOBIAN_STEP * np.maximum(1.0, np.abs(points[:, k]))
        plus = points.copy()
        minus = points.copy()
        plus[:, k] += step
        minus[:, k] -= step
        columns.append((residuals(plus) - residuals(minus)) / (2.0 * step)[:, None])
    return np.stack(columns, axis=2)


def isolated_tangencies(
    f: ParsedFunction,
    g: ParsedFunction,
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    values_f: np.ndarray,
    values_g: np.ndarray,
) -> np.ndarray:
    """Điểm tiếp xúc giữa hai mặt ẩn 3D: nghiệm chung mà hai mặt chạm nhau mà không đổi dấu.

    Cực tiểu địa phương của ``F² + G²`` (đã chuẩn hóa theo độ lớn mỗi hàm) trên 26 lân cận được dùng
    làm điểm khởi đầu, rồi tinh chỉnh bằng Gauss–Newton. Chỉ nhận điểm nằm trong lưới và có phần dư
    nhỏ. Các điểm trùng nhau được gộp.

    Args:
        f: Phương trình ẩn thứ nhất.
        g: Phương trình ẩn thứ hai.
        xs: Vector x của lưới.
        ys: Vector y của lưới.
        zs: Vector z của lưới.
        values_f: Giá trị ``F`` trên lưới, hình dạng ``(len(xs), len(ys), len(zs))``.
        values_g: Giá trị ``G`` trên lưới.

    Returns:
        Mảng ``(k, 3)`` các điểm tiếp xúc. Rỗng nếu không có.
    """
    scale_f = _finite_max(values_f)
    scale_g = _finite_max(values_g)
    if scale_f <= 0.0 or scale_g <= 0.0:
        return np.empty((0, 3))
    with np.errstate(invalid="ignore"):
        merit = (values_f / scale_f) ** 2 + (values_g / scale_g) ** 2
    merit = np.where(np.isfinite(merit), merit, np.inf)

    is_min = merit <= TANGENT_SCREEN
    padded = np.pad(merit, 1, constant_values=np.inf)
    shape = merit.shape
    for di, dj, dk in product((-1, 0, 1), repeat=3):
        if di == dj == dk == 0:
            continue
        neighbour = padded[1 + di : 1 + di + shape[0], 1 + dj : 1 + dj + shape[1], 1 + dk : 1 + dk + shape[2]]
        is_min &= merit <= neighbour

    index = np.argwhere(is_min)
    if index.size == 0:
        return np.empty((0, 3))
    order = np.argsort(merit[index[:, 0], index[:, 1], index[:, 2]])[:TANGENT_MAX_STARTS]
    index = index[order]
    starts = np.column_stack([xs[index[:, 0]], ys[index[:, 1]], zs[index[:, 2]]])

    residuals = implicit_residuals(f, g)
    refined = project_points(residuals, starts)
    span = np.array([xs[-1] - xs[0], ys[-1] - ys[0], zs[-1] - zs[0]])
    lower = np.array([xs[0], ys[0], zs[0]])
    upper = np.array([xs[-1], ys[-1], zs[-1]])
    inside = np.all((refined >= lower) & (refined <= upper), axis=1)
    tolerance = RESIDUAL_TOLERANCE * np.array([max(1.0, scale_f), max(1.0, scale_g)])
    good = inside & residual_norm_ok(residuals, refined, tolerance)
    return _merge_close_points(refined[good], 1e-6 * float(np.max(span)))


def _finite_max(values: np.ndarray) -> float:
    """Giá trị tuyệt đối lớn nhất trong các phần tử hữu hạn, hoặc 0 nếu không có."""
    finite = np.abs(values[np.isfinite(values)])
    return float(finite.max()) if finite.size else 0.0


def _merge_close_points(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Gộp các điểm cách nhau nhỏ hơn ``tolerance`` thành một, giữ thứ tự đầu tiên.

    Args:
        points: Các điểm ``(N, 3)``.
        tolerance: Khoảng cách gộp.

    Returns:
        Mảng điểm đã gộp.
    """
    kept: list[np.ndarray] = []
    for point in points:
        if not any(np.linalg.norm(point - other) <= tolerance for other in kept):
            kept.append(point)
    return np.array(kept).reshape(-1, 3)
