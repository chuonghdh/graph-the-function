"""Phân tích tự động mọi phương trình người dùng nhập và nhận diện không gian 2D hay 3D.

Người dùng không chọn loại phương trình. Module này quét các biến SymPy xuất hiện trong
biểu thức rồi phân loại theo bảng sau:

============================ ================= ======== ==================================
Dạng nhập                    Loại              Chiều    Ý nghĩa
============================ ================= ======== ==================================
``y = g(x)``                 ``explicit_y``    2D       đồ thị hàm số
``z = f(x, y)``              ``explicit_z``    3D       mặt cong
``A = B``                    ``implicit``      2D/3D    tập nghiệm của ``A − B = 0``
``biểu thức`` (không ``=``)  ``implicit`` hoặc ``explicit_y``  theo biến xuất hiện
============================ ================= ======== ==================================

Quy tắc nhỏ: biểu thức không có dấu ``=`` mà không chứa ``y`` hay ``z`` được hiểu là
``y = biểu thức``. Biểu thức chứa ``y`` hoặc ``z`` được hiểu là ``biểu thức = 0``.

Chiều của toàn hệ thống là 3D nếu ít nhất một ô nhập chứa ``z``, dù ô đó có đúng cú pháp hay không.

Module này không phụ thuộc Streamlit.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import sympy as sp

from graph_app.math_engine import (
    VARIABLE_SYMBOLS,
    ExpressionError,
    ParsedFunction,
    _IDENTIFIER,
    compile_expression,
    sympify_expression,
)

Dimension = Literal["2d", "3d"]
Kind = Literal["explicit_y", "explicit_z", "implicit"]

_ALL_VARIABLES: tuple[str, ...] = ("x", "y", "z")
_UNSUPPORTED_RELATION = re.compile(r"[<>!]=|==")
"""Các phép so sánh không phải dấu bằng đơn. Chỉ hỗ trợ phương trình, không hỗ trợ bất đẳng thức."""


@dataclass(frozen=True)
class UserEquation:
    """Một phương trình đã phân tích và đã được nhận diện chiều.

    Attributes:
        text: Chuỗi gốc do người dùng nhập.
        kind: ``"explicit_y"`` cho ``y = g(x)``, ``"explicit_z"`` cho ``z = f(x, y)``,
            ``"implicit"`` cho ``F = 0``.
        dimension: ``"3d"`` nếu phương trình chứa ``z``, ngược lại ``"2d"``.
        func: Hàm dùng để vẽ trực tiếp. Với ``explicit_y`` là ``g(x)``, với ``explicit_z``
            là ``f(x, y)``, với implicit là ``F`` theo đúng chiều của phương trình.
        implicit_2d: Dạng ``F(x, y) = 0``. ``None`` nếu phương trình chứa ``z``.
        implicit_3d: Dạng ``F(x, y, z) = 0``, luôn có. Dùng để vẽ mặt ẩn trong chế độ 3D.
    """

    text: str
    kind: Kind
    dimension: Dimension
    func: ParsedFunction
    implicit_2d: ParsedFunction | None
    implicit_3d: ParsedFunction

    @property
    def is_explicit_y(self) -> bool:
        """``True`` nếu phương trình có dạng ``y = g(x)``."""
        return self.kind == "explicit_y"

    @property
    def is_explicit_z(self) -> bool:
        """``True`` nếu phương trình có dạng ``z = f(x, y)``."""
        return self.kind == "explicit_z"


def parse_user_equation(text: str) -> UserEquation:
    """Phân tích một ô nhập và tự nhận diện loại phương trình và chiều.

    Args:
        text: Chuỗi người dùng nhập, ví dụ ``"sin(x)"``, ``"y = x^2 + 2x + 1"``,
            ``"z = x**2 + y**2"``, ``"x**2 + y**2 = 25"`` hoặc ``"x**2 + y**2 + z**2 = 16"``.

    Returns:
        ``UserEquation`` đã phân loại và đã biên dịch.

    Raises:
        ExpressionError: Khi cú pháp sai, có nhiều dấu ``=``, có bất đẳng thức, vế trống,
            hoặc chứa biến ngoài ``x``, ``y``, ``z``.
    """
    stripped = text.strip()
    lhs, rhs = _split_equation(stripped)

    if rhs is None:
        expr = sympify_expression(stripped, _ALL_VARIABLES)
        names = _names(expr)
        if "z" in names or "y" in names:
            return _implicit(stripped, expr)
        return _explicit_y(stripped, expr)

    lhs_expr = sympify_expression(lhs, _ALL_VARIABLES)
    rhs_expr = sympify_expression(rhs, _ALL_VARIABLES)
    rhs_names = _names(rhs_expr)

    if lhs.strip() == "y" and rhs_names <= {"x"}:
        return _explicit_y(stripped, rhs_expr)
    if lhs.strip() == "z" and rhs_names <= {"x", "y"}:
        return _explicit_z(stripped, rhs_expr)
    return _implicit(stripped, lhs_expr - rhs_expr)


def parse_all_equations(texts: Sequence[str]) -> tuple[dict[int, UserEquation], list[str]]:
    """Phân tích mọi ô nhập không rỗng và gom lỗi theo tên ô.

    Args:
        texts: Nội dung các ô, theo thứ tự ``f1``, ``f2``, ``f3``.

    Returns:
        Cặp ``(equations, errors)``. ``equations`` ánh xạ chỉ số ô (từ 0) sang phương trình.
        ``errors`` là các thông báo tiếng Việt, mở đầu bằng tên ô bị lỗi.
    """
    equations: dict[int, UserEquation] = {}
    errors: list[str] = []
    for index, text in enumerate(texts):
        if not text.strip():
            continue
        try:
            equations[index] = parse_user_equation(text)
        except ExpressionError as exc:
            errors.append(f"**f{index + 1}**: {exc}")
    return equations, errors


def detect_dimension(equations: dict[int, UserEquation], texts: Sequence[str]) -> Dimension:
    """Xác định chiều của toàn hệ thống từ các ô nhập.

    Chế độ 3D được chọn nếu có ít nhất một phương trình 3D, hoặc có ô nào nhắc đến ``z``
    dù phương trình đó lỗi cú pháp. Điều này giúp người dùng thấy rõ lỗi trong không gian 3D
    thay vì bị chuyển về 2D một cách khó hiểu.

    Args:
        equations: Phương trình đã phân tích thành công.
        texts: Nội dung mọi ô nhập, kể cả ô lỗi.

    Returns:
        ``"3d"`` hoặc ``"2d"``.
    """
    if any(eq.dimension == "3d" for eq in equations.values()):
        return "3d"
    if any("z" in _IDENTIFIER.findall(text) for text in texts):
        return "3d"
    return "2d"


def _explicit_y(text: str, expr: sp.Basic) -> UserEquation:
    """Đóng gói ``y = g(x)``, với ``g`` là ``expr``. Dạng ẩn là ``y − g(x)``."""
    implicit_expr = VARIABLE_SYMBOLS["y"] - expr
    return UserEquation(
        text=text,
        kind="explicit_y",
        dimension="2d",
        func=compile_expression(text, expr, ("x",)),
        implicit_2d=compile_expression(text, implicit_expr, ("x", "y")),
        implicit_3d=compile_expression(text, implicit_expr, _ALL_VARIABLES),
    )


def _explicit_z(text: str, expr: sp.Basic) -> UserEquation:
    """Đóng gói ``z = f(x, y)``, với ``f`` là ``expr``. Dạng ẩn là ``z − f(x, y)``."""
    implicit_expr = VARIABLE_SYMBOLS["z"] - expr
    return UserEquation(
        text=text,
        kind="explicit_z",
        dimension="3d",
        func=compile_expression(text, expr, ("x", "y")),
        implicit_2d=None,
        implicit_3d=compile_expression(text, implicit_expr, _ALL_VARIABLES),
    )


def _implicit(text: str, expr: sp.Basic) -> UserEquation:
    """Đóng gói ``F = 0``. Chiều được suy ra từ việc ``F`` có chứa ``z`` hay không."""
    if "z" in _names(expr):
        return UserEquation(
            text=text,
            kind="implicit",
            dimension="3d",
            func=compile_expression(text, expr, _ALL_VARIABLES),
            implicit_2d=None,
            implicit_3d=compile_expression(text, expr, _ALL_VARIABLES),
        )
    return UserEquation(
        text=text,
        kind="implicit",
        dimension="2d",
        func=compile_expression(text, expr, ("x", "y")),
        implicit_2d=compile_expression(text, expr, ("x", "y")),
        implicit_3d=compile_expression(text, expr, _ALL_VARIABLES),
    )


def _names(expr: sp.Basic) -> set[str]:
    """Tên các biến thật sự xuất hiện trong biểu thức, ví dụ ``{"x", "z"}``."""
    return {str(symbol) for symbol in expr.free_symbols}


def _split_equation(text: str) -> tuple[str, str | None]:
    """Tách chuỗi quanh dấu ``=`` đơn.

    Args:
        text: Chuỗi cần tách.

    Returns:
        ``(lhs, rhs)`` nếu có đúng một dấu ``=``; ``(text, None)`` nếu không có dấu ``=``.

    Raises:
        ExpressionError: Khi có bất đẳng thức, nhiều dấu ``=``, hoặc một vế bị trống.
    """
    if _UNSUPPORTED_RELATION.search(text):
        raise ExpressionError(
            "Chỉ hỗ trợ phương trình với dấu '='. Bất đẳng thức như <, >, <=, >= chưa được hỗ trợ."
        )
    count = text.count("=")
    if count == 0:
        return text, None
    if count > 1:
        raise ExpressionError("Chỉ được dùng đúng một dấu '=' trong phương trình.")
    lhs, rhs = (part.strip() for part in text.split("="))
    if not lhs or not rhs:
        raise ExpressionError("Thiếu vế bên trái hoặc bên phải của dấu '='. Ví dụ: x^2 + y^2 = 25.")
    return lhs, rhs
