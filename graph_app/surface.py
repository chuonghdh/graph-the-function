"""Lõi tính toán 3D: tạo lưới, tính mặt z = f(x, y) và tìm đường giao giữa hai mặt.

Giống ``math_engine``, module này không phụ thuộc Streamlit.

Luồng xử lý:
    khoảng x, y → ``make_grid`` → ``evaluate_surface`` (mảng Z trên lưới)
    → ``intersection_curves`` (các đường mức Z₁ − Z₂ = 0, chiếu lên mặt phẳng xy)
    → điểm ba chiều (x, y, z) để vẽ đường giao.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from contourpy import contour_generator

from graph_app.math_engine import ParsedFunction
from graph_app.refine import RESIDUAL_TOLERANCE, project_points, residual_norm_ok

DEFAULT_RESOLUTION: int = 100
"""Số điểm mỗi chiều của lưới mặc định. Lưới 100×100 cho 10 nghìn đỉnh, đủ mượt và nhanh."""

MAX_RESOLUTION: int = 200
"""Giới hạn số điểm mỗi chiều. Vượt quá mức này, trình duyệt sẽ chậm khi xoay hình."""

_IDENTICAL_TOLERANCE: float = 1e-12
"""Nếu ``|Z₁ − Z₂|`` nhỏ hơn ngưỡng này ở mọi đỉnh thì hai mặt trùng nhau."""


@dataclass(frozen=True)
class Surface:
    """Một mặt z = f(x, y) đã tính trên lưới.

    Attributes:
        label: Tên hiển thị, ví dụ ``"z1 = x^2 + y^2"``.
        xs: Vector hoành độ của lưới, độ dài ``nx``.
        ys: Vector tung độ của lưới, độ dài ``ny``.
        zs: Ma trận giá trị, hình dạng ``(ny, nx)``. ``NaN`` tại điểm không xác định.
    """

    label: str
    xs: np.ndarray
    ys: np.ndarray
    zs: np.ndarray


@dataclass(frozen=True)
class SpacePolyline:
    """Một đường cong trong không gian, gồm các điểm (x, y, z) đã sắp thứ tự.

    Attributes:
        points: Mảng hình dạng ``(n, 3)`` với các cột x, y, z.
    """

    points: np.ndarray


def make_grid(
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    resolution: int = DEFAULT_RESOLUTION,
) -> tuple[np.ndarray, np.ndarray]:
    """Tạo hai vector tọa độ đều cho lưới 3D.

    Chỉ trả về hai vector 1 chiều thay vì ``np.meshgrid`` đầy đủ, vì Plotly ``Surface``
    nhận trực tiếp ``x`` và ``y`` dạng vector, còn hàm được broadcast trên lưới khi tính Z.

    Args:
        x_range: Cặp ``(x_min, x_max)``.
        y_range: Cặp ``(y_min, y_max)``.
        resolution: Số điểm mỗi chiều, từ 2 đến ``MAX_RESOLUTION``.

    Returns:
        Cặp vector ``(xs, ys)``.

    Raises:
        ValueError: Khi khoảng rỗng hoặc đảo ngược, hoặc độ phân giải nằm ngoài giới hạn.
    """
    x_min, x_max = x_range
    y_min, y_max = y_range
    if x_min >= x_max or y_min >= y_max:
        raise ValueError("Cận dưới phải nhỏ hơn cận trên trên cả hai trục.")
    if not 2 <= resolution <= MAX_RESOLUTION:
        raise ValueError(f"Độ phân giải phải nằm trong khoảng 2 đến {MAX_RESOLUTION}.")
    return np.linspace(x_min, x_max, resolution), np.linspace(y_min, y_max, resolution)


def evaluate_surface(func: ParsedFunction, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Tính giá trị z = f(x, y) trên toàn bộ lưới.

    Args:
        func: Hàm hai biến đã phân tích, có ``variables == ("x", "y")``.
        xs: Vector hoành độ, độ dài ``nx``.
        ys: Vector tung độ, độ dài ``ny``.

    Returns:
        Ma trận ``Z`` hình dạng ``(ny, nx)``, ``Z[j, i] = f(xs[i], ys[j])``.
        Điểm không xác định có giá trị ``NaN``.

    Raises:
        ValueError: Khi hàm không đúng hai biến ``x`` và ``y``.
    """
    if func.variables != ("x", "y"):
        raise ValueError("Hàm 3D phải có đúng hai biến x và y.")
    grid_x, grid_y = np.meshgrid(xs, ys)
    return func(grid_x, grid_y)


def intersection_curves(
    surface_a: Surface,
    surface_b: Surface,
    func_a: ParsedFunction,
    func_b: ParsedFunction | None = None,
) -> list[SpacePolyline]:
    """Tìm đường giao của hai mặt, tức tập điểm mà z₁ = z₂.

    Ta tìm đường mức ``h(x, y) = Z₁ − Z₂ = 0`` trên lưới bằng ``contourpy``, rồi
    nâng từng điểm lên mặt phẳng bằng cách tính lại ``z = f₁(x, y)`` tại điểm đó.
    Nhờ vậy đường giao nằm chính xác trên mặt thứ nhất, không phụ thuộc độ phân giải lưới.

    Args:
        surface_a: Mặt thứ nhất. Tọa độ z của đường giao lấy theo mặt này.
        surface_b: Mặt thứ hai. Phải có cùng lưới với ``surface_a``.
        func_a: Hàm đã phân tích tương ứng với ``surface_a``, dùng để tính z chính xác.
        func_b: Hàm đã phân tích tương ứng với ``surface_b``. Nếu có, mỗi điểm được chiếu về đúng
            đường ``f₁ − f₂ = 0`` bằng Gauss–Newton, thay vì chỉ nội suy trên lưới.

    Returns:
        Danh sách các đường giao rời nhau. Trả về rỗng nếu hai mặt không cắt nhau
        trong miền, hoặc trùng nhau hoàn toàn (khi đó giao là cả một mặt, không phải đường).

    Raises:
        ValueError: Khi hai mặt không cùng lưới.
    """
    if not (np.array_equal(surface_a.xs, surface_b.xs) and np.array_equal(surface_a.ys, surface_b.ys)):
        raise ValueError("Hai mặt phải được tính trên cùng một lưới.")

    diff = surface_a.zs - surface_b.zs
    finite = np.isfinite(diff)
    if not finite.any():
        return []
    finite_a = np.abs(surface_a.zs[np.isfinite(surface_a.zs)])
    scale = max(1.0, float(np.max(finite_a, initial=0.0)))
    if np.max(np.abs(diff[finite])) <= _IDENTICAL_TOLERANCE * scale:
        return []

    generator = contour_generator(surface_a.xs, surface_a.ys, diff)
    cell = 2.0 * float(np.hypot(surface_a.xs[1] - surface_a.xs[0], surface_a.ys[1] - surface_a.ys[0]))
    polylines: list[SpacePolyline] = []
    for line_xy in generator.lines(0.0):
        if len(line_xy) < 2:
            continue
        if func_b is not None:
            line_xy = _refine_on_difference(func_a, func_b, line_xy, cell)
        line_x = line_xy[:, 0]
        line_y = line_xy[:, 1]
        line_z = func_a(line_x, line_y)
        # Bỏ các đoạn rơi vào vùng không xác định: giữ điểm hữu hạn để đường không bị đứt vô nghĩa.
        valid = np.isfinite(line_z)
        if valid.sum() < 2:
            continue
        polylines.append(SpacePolyline(points=np.column_stack([line_x[valid], line_y[valid], line_z[valid]])))
    return polylines


def _refine_on_difference(
    func_a: ParsedFunction,
    func_b: ParsedFunction,
    xy: np.ndarray,
    max_move: float,
) -> np.ndarray:
    """Chiếu các điểm ``(x, y)`` về đường ``f₁(x, y) − f₂(x, y) = 0``.

    Args:
        func_a: Hàm z của mặt thứ nhất.
        func_b: Hàm z của mặt thứ hai.
        xy: Các điểm ``(n, 2)`` từ đường mức.
        max_move: Độ trôi tối đa cho phép. Điểm trôi xa hơn thì giữ nguyên.

    Returns:
        Mảng ``(n, 2)`` các điểm đã chiếu.
    """

    def residuals(points: np.ndarray) -> np.ndarray:
        """Hiệu z của hai mặt tại từng điểm, dạng cột ``(N, 1)``."""
        return (func_a(points[:, 0], points[:, 1]) - func_b(points[:, 0], points[:, 1]))[:, None]

    moved = project_points(residuals, xy)
    ok = (
        np.isfinite(moved).all(axis=1)
        & (np.linalg.norm(moved - xy, axis=1) <= max_move)
        & residual_norm_ok(residuals, np.where(np.isfinite(moved), moved, xy), np.array([RESIDUAL_TOLERANCE]))
    )
    return np.where(ok[:, None], moved, xy)
