"""Lõi tính toán toán học: phân tích biểu thức an toàn, lấy mẫu và tìm giao điểm 2D.

Module này không phụ thuộc Streamlit, nhờ vậy có thể kiểm thử độc lập.

Luồng xử lý chính:
    chuỗi nhập vào → ``parse_expression`` → ``ParsedFunction`` (gọi được như hàm NumPy)
    → ``find_intersections`` tìm nghiệm của ``f(x) - g(x) = 0``.

Phương trình ``A = B`` được xử lý ở ``graph_app.equations``, dùng lại các hàm
``sympify_expression`` và ``compile_expression`` của module này.
"""

from __future__ import annotations

import re
import tokenize
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

MAX_EXPRESSION_LENGTH: int = 200
"""Độ dài tối đa của một biểu thức, chặn chuỗi quá lớn gây chậm bộ phân tích."""

DEFAULT_SAMPLES: int = 2000
"""Số điểm lấy mẫu mặc định khi vẽ và khi dò giao điểm trên một khoảng."""

_ROOT_XTOL: float = 1e-14
"""Sai số hoành độ tuyệt đối khi giải bằng ``brentq`` và tối ưu hóa cực tiểu (gần float64)."""
_BISECTION_STEPS: int = 60
"""Số lần chia đôi khi giải đoạn đổi dấu. 60 lần thu hẹp đoạn rộng 0.004 xuống dưới độ chính xác float64."""
_DEDUP_RELATIVE_GAP: float = 1e-9
"""Ngưỡng gộp hai nghiệm, theo tỉ lệ độ rộng khoảng. Đủ nhỏ để không gộp hai nghiệm sát nhau thật."""
_POLY_DIGITS: int = 30
"""Số chữ số thập phân khi SymPy tính nghiệm đa thức bằng số."""
_POLY_MAX_STEPS: int = 500
"""Số bước lặp tối đa của ``Poly.nroots``; đủ cho đa thức bậc thấp trong ứng dụng."""
_BOUNDARY_TOLERANCE: float = 1e-6
"""Ngưỡng kiểm tra nghiệm nằm ở mép miền xác định. Căn bậc hai tại mép cho sai số cỡ √(sai số x)."""
_IMAG_TOLERANCE: float = 1e-10
"""Phần ảo tối đa để coi một nghiệm phức của đa thức là nghiệm thực."""
_TANGENT_SCREEN: float = 0.05
"""Chỉ thử tìm tiếp xúc tại cực tiểu của ``|h|`` nhỏ hơn 5% độ lớn hai hàm."""

_RELATIVE_TOLERANCE: float = 1e-9
"""Sai số tương đối để coi ``f(x) - g(x)`` là bằng 0 khi xác nhận một giao điểm."""

_ZERO_SNAP: float = 1e-12
"""Giá trị tuyệt đối nhỏ hơn ngưỡng này được coi là 0 khi hiển thị giao điểm."""

_IDENTICAL_TOLERANCE: float = 1e-12
"""Nếu ``|f - g|`` nhỏ hơn ngưỡng này trên mọi điểm thì hai hàm coi như trùng nhau."""

_X = sp.Symbol("x", real=True)
_Y = sp.Symbol("y", real=True)
_Z = sp.Symbol("z", real=True)

VARIABLE_SYMBOLS: dict[str, sp.Symbol] = {"x": _X, "y": _Y, "z": _Z}
"""Các biến được hỗ trợ. 2D dùng ``x``, 3D dùng ``x`` và ``y``, mặt ẩn 3D dùng cả ``z``."""

# Danh sách tên được phép xuất hiện trong biểu thức. Mọi tên khác đều bị từ chối,
# nên không thể gọi thuộc tính, hàm hệ thống hay tên bắt đầu bằng "_".
# Việc biểu thức có được dùng biến nào do tham số ``variables`` quyết định.
_ALLOWED_NAMES: dict[str, object] = {
    "x": _X,
    "y": _Y,
    "z": _Z,
    "pi": sp.pi,
    "e": sp.E,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "cot": sp.cot,
    "sec": sp.sec,
    "csc": sp.csc,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "arcsin": sp.asin,
    "arccos": sp.acos,
    "arctan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "sqrt": sp.sqrt,
    # "log" và "ln" đều là logarit tự nhiên, theo quy ước của Python và SymPy.
    "log": sp.log,
    "ln": sp.log,
    "log10": lambda t: sp.log(t, 10),
    "log2": lambda t: sp.log(t, 2),
    "abs": sp.Abs,
}

# Chỉ cho phép chữ, số, khoảng trắng và các toán tử + - * / ^ ( ) . ; mọi ký tự khác bị loại.
_ALLOWED_CHARS = re.compile(r"[0-9A-Za-z\s+\-*/^().]*")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_LETTERS_ONLY = re.compile(r"[a-z]{2,}")
_LETTER_DIGITS = re.compile(r"([a-z])(\d+)")

_SYNTAX_TIP = (
    "Mẹo: dùng `*` để nhân (2*x), `**` hoặc `^` để lũy thừa (x^2), "
    "và đặt đối số hàm trong ngoặc (sin(x))."
)
"""Gợi ý chung, hiển thị kèm mọi lỗi cú pháp."""

# Namespace nội bộ mà SymPy cần khi dựng cây biểu thức (Add, Mul, Pow, ...).
# Không chứa __builtins__ nên không thể gọi hàm Python tích hợp. Người dùng chỉ
# gõ được tên trong _ALLOWED_NAMES nhờ kiểm tra ở _validate_tokens.
_SYMPY_NAMESPACE: dict[str, object] = {"__builtins__": {}} | {
    name: getattr(sp, name) for name in dir(sp) if not name.startswith("_")
}

_TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,  # cho phép "2x", "2sin(x)"
    convert_xor,  # cho phép "x^2" thay cho "x**2"
)


class ExpressionError(ValueError):
    """Biểu thức nhập vào không hợp lệ. Thông báo đã được viết sẵn bằng tiếng Việt."""


@dataclass(frozen=True)
class Intersection:
    """Một giao điểm của hai đồ thị.

    Attributes:
        x: Hoành độ giao điểm.
        y: Tung độ giao điểm, tính theo hàm thứ nhất.
    """

    x: float
    y: float


@dataclass(frozen=True)
class ParsedFunction:
    """Hàm số đã được phân tích và biên dịch thành hàm NumPy.

    Attributes:
        text: Chuỗi gốc do người dùng nhập, dùng để hiển thị chú thích.
        expr: Biểu thức SymPy tương ứng.
        variables: Tên các biến theo đúng thứ tự tham số khi gọi hàm, ví dụ ``("x",)``,
            ``("x", "y")`` hoặc ``("x", "y", "z")``.
    """

    text: str
    expr: sp.Basic
    _func: Callable[..., object]
    variables: tuple[str, ...] = ("x",)

    def __call__(self, *args: np.ndarray | float) -> np.ndarray:
        """Tính giá trị hàm tại các điểm đầu vào, theo đúng thứ tự ``variables``.

        Args:
            *args: Một mảng hoặc số cho mỗi biến. Các mảng được broadcast với nhau.

        Returns:
            Mảng float có hình dạng broadcast của đầu vào. Điểm không xác định
            (chia 0, ngoài miền xác định, tràn số) có giá trị ``NaN``.

        Raises:
            ValueError: Khi số đối số khác số biến của hàm.
        """
        if len(args) != len(self.variables):
            raise ValueError(f"Cần {len(self.variables)} đối số, nhận được {len(args)}.")
        arrays = [np.asarray(a, dtype=float) for a in args]
        shape = np.broadcast_shapes(*(a.shape for a in arrays))
        # Lỗi chia 0, log(âm), sqrt(âm) là hành vi bình thường khi vẽ, không cần cảnh báo.
        with np.errstate(all="ignore"):
            raw = self._func(*arrays)
        if np.iscomplexobj(raw):
            # Căn bậc chẵn của số âm có thể sinh phần ảo; chỉ giữ phần thực, bỏ điểm ảo.
            raw = np.where(np.abs(np.imag(raw)) < 1e-12, np.real(raw), np.nan)
        result = np.broadcast_to(np.asarray(raw, dtype=float), shape).copy()
        result[~np.isfinite(result)] = np.nan
        return result


def parse_expression(text: str, variables: tuple[str, ...] = ("x",)) -> ParsedFunction:
    """Phân tích chuỗi nhập vào thành hàm số theo các biến cho trước.

    Args:
        text: Biểu thức, ví dụ ``"sin(x) + x^2/3"`` hoặc ``"x**2 + y**2"``.
            Chấp nhận ``π`` thay cho ``pi``.
        variables: Các biến cho phép, theo thứ tự tham số của hàm.

    Returns:
        Đối tượng ``ParsedFunction`` sẵn sàng để tính giá trị.

    Raises:
        ExpressionError: Biểu thức rỗng, quá dài, chứa ký tự hoặc tên không được phép,
            cú pháp sai, hoặc chứa biến không nằm trong ``variables``.
    """
    expr = sympify_expression(text, variables)
    return compile_expression(text, expr, variables)


def sympify_expression(text: str, variables: tuple[str, ...]) -> sp.Basic:
    """Phân tích chuỗi thành biểu thức SymPy an toàn, chưa biên dịch.

    Quy trình: tiền xử lý, kiểm tra ký tự và tên, phân tích bằng SymPy với danh sách
    hàm được phép, rồi đổi mọi số nguyên thành số thực.

    Args:
        text: Chuỗi biểu thức, không chứa dấu ``=``.
        variables: Các biến cho phép.

    Returns:
        Biểu thức SymPy chỉ chứa các biến trong ``variables``.

    Raises:
        ExpressionError: Khi chuỗi không hợp lệ theo bất kỳ quy tắc nào ở trên.
    """
    cleaned = _replace_abs_bars(text.strip().replace("π", "pi"))
    _validate_tokens(cleaned)
    symbols = [VARIABLE_SYMBOLS[name] for name in variables]

    try:
        expr = parse_expr(
            cleaned,
            local_dict=dict(_ALLOWED_NAMES),
            global_dict=dict(_SYMPY_NAMESPACE),
            transformations=_TRANSFORMATIONS,
            # Không tự rút gọn: giữ nguyên biểu thức như người dùng viết và tránh tính
            # trước các phép lũy thừa số lớn như 9**9**9.
            evaluate=False,
        )
    except (SyntaxError, TypeError, ValueError, sp.SympifyError, tokenize.TokenError) as exc:
        raise ExpressionError(f"Cú pháp không hợp lệ: '{text.strip()}'. {_SYNTAX_TIP}") from exc

    if not isinstance(expr, sp.Basic):
        raise ExpressionError(f"Không nhận dạng được biểu thức: '{text.strip()}'. {_SYNTAX_TIP}")

    extra_symbols = expr.free_symbols - set(symbols)
    if extra_symbols:
        names = ", ".join(sorted(str(s) for s in extra_symbols))
        allowed = ", ".join(variables)
        raise ExpressionError(f"Chỉ được dùng biến {allowed}. Phát hiện thêm: {names}.")

    # Đổi số nguyên thành số thực để NumPy tính bằng float64. Nếu giữ số nguyên,
    # Python sẽ tính trước lũy thừa khổng lồ như 10**(10**10) và treo ứng dụng.
    return expr.xreplace({atom: sp.Float(atom) for atom in expr.atoms(sp.Integer)})


def _replace_abs_bars(text: str) -> str:
    """Đổi cặp ký hiệu ``|…|`` thành ``abs(…)`` để người dùng có thể viết trị tuyệt đối tự nhiên.

    Các cặp ``|`` được ghép theo thứ tự xuất hiện: dấu đầu là mở, dấu tiếp theo là đóng.

    Args:
        text: Chuỗi biểu thức đã loại khoảng trắng đầu cuối.

    Returns:
        Chuỗi với ``|…|`` được thay bằng ``abs(…)``.

    Raises:
        ExpressionError: Khi số dấu ``|`` là lẻ.
    """
    pieces: list[str] = []
    opened = False
    for char in text:
        if char == "|":
            pieces.append(")" if opened else "abs(")
            opened = not opened
        else:
            pieces.append(char)
    if opened:
        raise ExpressionError("Thiếu dấu '|' đóng trị tuyệt đối. Ví dụ: |x| hoặc abs(x).")
    return "".join(pieces)


def compile_expression(text: str, expr: sp.Basic, variables: tuple[str, ...]) -> ParsedFunction:
    """Biên dịch biểu thức SymPy thành hàm NumPy vector hóa.

    Args:
        text: Chuỗi gốc, lưu lại để hiển thị.
        expr: Biểu thức đã qua ``sympify_expression``.
        variables: Thứ tự tham số của hàm kết quả.

    Returns:
        ``ParsedFunction`` sẵn sàng để gọi.
    """
    symbols = [VARIABLE_SYMBOLS[name] for name in variables]
    func = sp.lambdify(symbols, expr, modules="numpy")
    return ParsedFunction(text=text.strip(), expr=expr, _func=func, variables=variables)


def _validate_tokens(text: str) -> None:
    """Kiểm tra độ dài, ký tự và tên trước khi đưa vào bộ phân tích.

    Args:
        text: Chuỗi đã loại khoảng trắng đầu cuối.

    Raises:
        ExpressionError: Khi chuỗi rỗng, quá dài, có ký tự lạ hoặc có tên không được phép.
    """
    if not text:
        raise ExpressionError("Biểu thức đang trống. Hãy nhập một hàm, ví dụ x^2 hoặc sin(x).")
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise ExpressionError(f"Biểu thức quá dài (tối đa {MAX_EXPRESSION_LENGTH} ký tự).")
    if _ALLOWED_CHARS.fullmatch(text) is None:
        bad = sorted({ch for ch in text if _ALLOWED_CHARS.fullmatch(ch) is None})
        shown = " ".join(f"'{ch}'" for ch in bad)
        raise ExpressionError(f"Ký tự {shown} không được phép trong biểu thức. {_SYNTAX_TIP}")

    for name in _IDENTIFIER.findall(text):
        if name not in _ALLOWED_NAMES:
            raise ExpressionError(f"Tên '{name}' không được hỗ trợ. {_name_hint(name)}")


def _name_hint(name: str) -> str:
    """Gợi ý cách viết đúng cho một tên không hợp lệ, thường gặp khi quên dấu ``*`` hoặc ``^``.

    Args:
        name: Tên không được phép, ví dụ ``xy`` hoặc ``x2``.

    Returns:
        Câu gợi ý tiếng Việt, hoặc chuỗi rỗng nếu không đoán được ý người dùng.
    """
    if _LETTERS_ONLY.fullmatch(name):
        return f"Nếu muốn nhân, viết {'*'.join(name)} (ví dụ xy → x*y)."
    match = _LETTER_DIGITS.fullmatch(name)
    if match:
        return f"Nếu muốn lũy thừa, viết {match.group(1)}^{match.group(2)} (ví dụ x2 → x^2)."
    return ""


def sample_function(
    func: ParsedFunction,
    x_min: float,
    x_max: float,
    samples: int = DEFAULT_SAMPLES,
) -> tuple[np.ndarray, np.ndarray]:
    """Lấy mẫu hàm số đều trên khoảng ``[x_min, x_max]``.

    Args:
        func: Hàm số cần lấy mẫu, một biến.
        x_min: Cận dưới của miền x.
        x_max: Cận trên của miền x, phải lớn hơn ``x_min``.
        samples: Số điểm lấy mẫu, tối thiểu 2.

    Returns:
        Cặp mảng ``(x, y)``. ``y`` có ``NaN`` tại điểm không xác định.

    Raises:
        ValueError: Khi ``x_min >= x_max`` hoặc ``samples < 2``.
    """
    _check_range(x_min, x_max, samples)
    x = np.linspace(x_min, x_max, samples)
    return x, func(x)


def find_intersections(
    f: ParsedFunction,
    g: ParsedFunction,
    x_min: float,
    x_max: float,
    samples: int = DEFAULT_SAMPLES,
) -> list[Intersection]:
    """Giải ``f(x) - g(x) = 0`` trên ``[x_min, x_max]`` và trả về các giao điểm ``(x, f(x))``.

    Việc tìm nghiệm tách khỏi việc vẽ đồ thị, theo hai nhánh:

    1. Nếu ``h = f - g`` là đa thức theo ``x``, giải đúng bằng SymPy (``Poly.nroots``).
       Cách này bắt được mọi nghiệm, kể cả nghiệm bội.
    2. Ngược lại, chia khoảng thành ``samples`` đoạn con, tìm các đoạn ``h`` đổi dấu
       (định lý Bolzano) rồi giải đồng loạt từng đoạn bằng chia đôi trên NumPy. Cặp nghiệm nằm chung một ô lưới được bắt
       bằng đỉnh parabol qua ba điểm lưới. Các cực tiểu địa phương
       của ``|h|`` mà ``h`` không đổi dấu được tối ưu hóa bằng ``minimize_scalar``
       để bắt tiếp xúc.

    Mọi ứng viên đều được kiểm tra lại ``|f - g|`` tại chính điểm đó. Nhờ vậy các điểm
    gián đoạn như tiệm cận của ``1/x`` không bị nhận nhầm thành giao điểm.

    Args:
        f: Hàm thứ nhất. Tung độ của giao điểm được tính theo hàm này.
        g: Hàm thứ hai.
        x_min: Cận dưới của khoảng tìm nghiệm.
        x_max: Cận trên của khoảng tìm nghiệm.
        samples: Số đoạn con để dò đổi dấu ở nhánh số. Chỉ dùng khi ``h`` không phải đa thức.

    Returns:
        Danh sách giao điểm đã sắp xếp theo ``x`` và đã loại trùng lặp.
        Trả về danh sách rỗng nếu hai hàm trùng nhau hoàn toàn.

    Raises:
        ValueError: Khi ``x_min >= x_max`` hoặc ``samples < 2``.
    """
    _check_range(x_min, x_max, samples)
    poly = _polynomial_difference(f, g)
    if poly is not None:
        candidates = _polynomial_roots(poly, x_min, x_max)
        trusted: list[float] = []
    else:
        candidates, trusted = _numeric_roots(f, g, x_min, x_max, samples)
    verified = [p.x for p in _verified_roots(candidates, f, g, x_min, x_max)]
    return _deduplicate(np.array(verified + trusted, dtype=float), f, x_min, x_max)


def _polynomial_difference(f: ParsedFunction, g: ParsedFunction) -> sp.Poly | None:
    """Trả về ``f - g`` dưới dạng đa thức một biến ``x``, hoặc ``None`` nếu không phải đa thức.

    Hàm siêu việt (sin, exp, log...) hoặc căn không phải đa thức, nên được giải bằng số.

    Args:
        f: Hàm thứ nhất.
        g: Hàm thứ hai.

    Returns:
        Đa thức SymPy theo ``x``, hoặc ``None``.
    """
    difference = sp.expand(f.expr - g.expr)
    # Phân tích đổi số nguyên thành Float (x**2 thành x**2.0), khiến SymPy không nhận là đa thức.
    # Đổi các Float nguyên hữu hạn về Integer để nhận diện đúng.
    difference = difference.xreplace(
        {a: sp.Integer(int(a)) for a in difference.atoms(sp.Float) if a.is_finite and float(a).is_integer()}
    )
    if not difference.is_polynomial(_X) or difference.free_symbols - {_X}:
        return None
    return sp.Poly(difference, _X)


def _polynomial_roots(poly: sp.Poly, x_min: float, x_max: float) -> list[float]:
    """Nghiệm thực của đa thức nằm trong khoảng, tính bằng ``Poly.nroots`` độ chính xác 30 chữ số.

    Args:
        poly: Đa thức ``f - g`` theo ``x``.
        x_min: Cận dưới của khoảng.
        x_max: Cận trên của khoảng.

    Returns:
        Danh sách hoành độ nghiệm thực. Nghiệm bội có thể xuất hiện nhiều lần.
    """
    # Đa thức đồng nhất 0 (hai hàm trùng nhau) hoặc hằng khác 0 đều không có giao điểm cô lập.
    if poly.is_zero or poly.degree() < 1:
        return []
    roots: list[float] = []
    for root in poly.nroots(n=_POLY_DIGITS, maxsteps=_POLY_MAX_STEPS):
        value = complex(root)
        if abs(value.imag) <= _IMAG_TOLERANCE and x_min <= value.real <= x_max:
            roots.append(value.real)
    return roots


def _numeric_roots(
    f: ParsedFunction,
    g: ParsedFunction,
    x_min: float,
    x_max: float,
    samples: int,
) -> tuple[list[float], list[float]]:
    """Tìm ứng viên nghiệm trên lưới bằng bốn nhóm: đổi dấu, cặp trong một ô, mép miền, tiếp xúc.

    Args:
        f: Hàm thứ nhất.
        g: Hàm thứ hai.
        x_min: Cận dưới của khoảng.
        x_max: Cận trên của khoảng.
        samples: Số điểm lưới.

    Returns:
        Cặp ``(ứng viên, nghiệm đã kiểm tra riêng)``. Ứng viên phải qua ``_verified_roots``. Nghiệm mép
        đã được kiểm tra với ngưỡng ``_BOUNDARY_TOLERANCE`` và không kiểm tra lại. Cả hai rỗng nếu
        hai hàm trùng nhau trên lưới.
    """
    xs = np.linspace(x_min, x_max, samples)
    h = f(xs) - g(xs)
    abs_h = np.abs(h)
    finite = np.isfinite(h)
    if not finite.any():
        return [], []
    scale = max(1.0, _max_abs(f(xs), g(xs)))
    # Hai hàm trùng nhau thì h = 0 ở mọi điểm, không phải giao điểm cô lập.
    if np.max(abs_h[finite]) <= _IDENTICAL_TOLERANCE * scale:
        return [], []

    def difference(t: np.ndarray) -> np.ndarray:
        """Hiệu ``f - g`` trên mảng điểm, ``NaN`` tại điểm một trong hai hàm không xác định."""
        return f(t) - g(t)

    # Nhóm 1: đoạn đổi dấu giữa hai điểm lưới liên tiếp. Điểm NaN không tạo đoạn đổi dấu.
    brackets = np.flatnonzero(h[:-1] * h[1:] < 0)
    # Nhóm 2: hai nghiệm nằm trong cùng một ô lưới, đầu mút cùng dấu nhưng đỉnh ngược dấu.
    pair_lo, pair_hi, pair_middle = _same_cell_pairs(xs, h, difference)
    roots = _bisect_roots(
        difference,
        np.concatenate([xs[brackets], pair_lo]),
        np.concatenate([xs[brackets + 1], pair_hi]),
    ).tolist()
    # Điểm lưới trúng đúng 0 là nghiệm cô lập. Nếu cạnh nó cũng bằng 0 thì đó là một đoạn trùng
    # nhau (vô số giao điểm), không liệt kê từng điểm. Ví dụ |x| = x trên tia x ≥ 0.
    zero = h == 0
    next_zero = np.concatenate([zero[1:], [False]])
    prev_zero = np.concatenate([[False], zero[:-1]])
    roots.extend(xs[zero & ~next_zero & ~prev_zero].tolist())
    # Đầu mút được thêm làm ứng viên; bước kiểm tra |f - g| sẽ quyết định, ví dụ
    # sin(2π) = -2.4e-16 trong float vẫn là nghiệm.
    roots.extend([x_min, x_max])

    # Nhóm 3: tiếp xúc, tức |h| chạm 0 tại cực tiểu mà h không đổi dấu. Bỏ qua cực tiểu nằm sát
    # một đoạn đổi dấu hoặc một cặp nghiệm, vì các nghiệm đó đã có. Chỉ thử cực tiểu đủ nhỏ để
    # tiết kiệm thời gian với hàm dao động dày, ví dụ sin(60x) có hàng nghìn cực tiểu.
    near_bracket = np.zeros(samples, dtype=bool)
    near_bracket[brackets] = True
    near_bracket[brackets + 1] = True
    near_bracket[pair_middle] = True
    near_bracket[pair_middle - 1] = True
    near_bracket[pair_middle + 1] = True
    scalar_difference = _difference_function(f, g)
    absolute = _abs_difference_function(scalar_difference)
    dip_lo: list[float] = []
    dip_hi: list[float] = []
    # Độ dốc cục bộ: chênh lệch lớn nhất với hai điểm lưới kề. Một vùng lõm nằm gọn trong một ô
    # có |h| ở điểm lưới nhỏ hơn độ dốc đó, nên ngưỡng sàng phải lấy theo độ dốc chứ không cố định.
    slope = np.zeros(samples)
    slope[1:] = np.abs(np.diff(h))
    slope[:-1] = np.maximum(slope[:-1], slope[1:])
    threshold = np.maximum(_TANGENT_SCREEN * scale, slope)
    for i in _local_minima(abs_h):
        if near_bracket[i] or abs_h[i] > threshold[i]:
            continue
        a = max(i - 1, 0)
        b = min(i + 1, samples - 1)
        result = minimize_scalar(
            absolute, bounds=(xs[a], xs[b]), method="bounded", options={"xatol": _ROOT_XTOL}
        )
        roots.append(float(result.x))
        # Hai nghiệm cách nhau nhỏ hơn bước lưới tạo một vùng lõm nằm giữa hai đầu cùng dấu. Cực
        # tiểu của |h| có thể hội tụ về một nghiệm bên cạnh, nên tìm đáy bằng cực trị của chính h
        # theo hướng ngược dấu với hai đầu. Nếu đáy đổi dấu thì mỗi nửa đoạn có một nghiệm.
        if h[a] * h[b] > 0:
            sign = np.sign(h[a])
            dip = minimize_scalar(
                lambda t: sign * scalar_difference(t),
                bounds=(xs[a], xs[b]),
                method="bounded",
                options={"xatol": _ROOT_XTOL},
            )
            x_dip = float(dip.x)
            h_dip = scalar_difference(x_dip)
            if np.isfinite(h_dip) and h_dip * h[a] < 0:
                dip_lo.extend([xs[a], x_dip])
                dip_hi.extend([x_dip, xs[b]])
    if dip_lo:
        roots.extend(_bisect_roots(difference, np.array(dip_lo), np.array(dip_hi)).tolist())
    trusted = _domain_edge_roots(difference, xs, finite, scale)
    return roots, trusted


def _domain_edge_roots(
    difference: Callable[[np.ndarray], np.ndarray],
    xs: np.ndarray,
    finite: np.ndarray,
    scale: float,
) -> list[float]:
    """Nghiệm nằm ở mép miền xác định, ví dụ √x = x/2 tại x = 0 (√x không xác định với x < 0).

    Tại mép hiệu không đổi dấu nên lưới không thấy được. Mép được tìm bằng chia đôi trên tính hữu
    hạn, rồi kiểm tra |h| tại phía hữu hạn với ngưỡng ``_BOUNDARY_TOLERANCE``. Ngưỡng này lớn hơn
    ngưỡng thường vì tại mép căn bậc hai cho |h| ~ √(sai số x).

    Args:
        difference: Hàm hiệu nhận mảng điểm.
        xs: Điểm lưới đều.
        finite: Mặt nạ các điểm lưới mà hiệu hữu hạn.
        scale: Độ lớn tham chiếu của hai hàm.

    Returns:
        Danh sách hoành độ mép đã qua kiểm tra.
    """
    edges = np.flatnonzero(finite[:-1] != finite[1:])
    if edges.size == 0:
        return []
    lo = xs[edges]
    hi = xs[edges + 1]
    lo_finite = finite[edges]
    for _ in range(_BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        same_as_lo = np.isfinite(difference(mid)) == lo_finite
        lo = np.where(same_as_lo, mid, lo)
        hi = np.where(same_as_lo, hi, mid)
    edge = np.where(lo_finite, lo, hi)
    values = np.abs(difference(edge))
    keep = np.isfinite(values) & (values <= _BOUNDARY_TOLERANCE * scale)
    return edge[keep].tolist()


def _same_cell_pairs(
    xs: np.ndarray,
    h: np.ndarray,
    difference: Callable[[np.ndarray], np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Tìm các ô lưới có thể chứa hai nghiệm: đầu mút cùng dấu nhưng đỉnh giữa ngược dấu.

    Đỉnh của parabol qua ba điểm lưới liên tiếp là điểm chia. Hai đoạn ``[đầu, đỉnh]`` và
    ``[đỉnh, cuối]`` đều đổi dấu, nên mỗi đoạn có ít nhất một nghiệm. Vị trí đỉnh chỉ là ước lượng,
    nên dấu được kiểm tra lại bằng ``difference`` tại đỉnh.

    Args:
        xs: Điểm lưới đều.
        h: Giá trị ``f - g`` tại các điểm lưới.
        difference: Hàm hiệu nhận mảng, để kiểm tra dấu tại đỉnh.

    Returns:
        Bộ ba ``(lo, hi, middle)``: các đầu mút của đoạn cần giải, và chỉ số điểm giữa của ô.
    """
    h0, h1, h2 = h[:-2], h[1:-1], h[2:]
    step = xs[1] - xs[0]
    with np.errstate(invalid="ignore", divide="ignore"):
        curvature = h0 - 2.0 * h1 + h2
        # Vị trí đỉnh tính theo số bước lưới, lệch so với điểm giữa.
        offset = 0.5 * (h0 - h2) / curvature
        vertex_value = h1 - 0.25 * (h0 - h2) * offset
        candidate = (
            (np.abs(offset) <= 1.0)
            & (np.sign(h0) == np.sign(h2))
            & (np.sign(vertex_value) == -np.sign(h0))
        )
    middle = np.flatnonzero(candidate) + 1
    if middle.size == 0:
        empty = np.empty(0)
        return empty, empty, np.empty(0, dtype=int)
    vertex_x = xs[middle] + offset[middle - 1] * step
    vertex_h = difference(vertex_x)
    keep = np.isfinite(vertex_h) & (np.sign(vertex_h) == -np.sign(h[middle - 1]))
    middle, vertex_x = middle[keep], vertex_x[keep]
    lo = np.concatenate([xs[middle - 1], vertex_x])
    hi = np.concatenate([vertex_x, xs[middle + 1]])
    return lo, hi, middle


def _bisect_roots(
    difference: Callable[[np.ndarray], np.ndarray],
    lo: np.ndarray,
    hi: np.ndarray,
) -> np.ndarray:
    """Giải đồng loạt nhiều đoạn đổi dấu bằng chia đôi trên mảng NumPy.

    Nhanh hơn ``brentq`` gọi từng nghiệm trong Python, vì mọi đoạn được thu hẹp cùng lúc. Đoạn
    không đổi dấu ở hai đầu, hoặc gặp ``NaN`` giữa chừng (ví dụ tiệm cận của ``1/x``), bị bỏ.

    Args:
        difference: Hàm hiệu nhận mảng điểm.
        lo: Đầu mút trái của mỗi đoạn.
        hi: Đầu mút phải của mỗi đoạn.

    Returns:
        Mảng hoành độ nghiệm đã tìm, có thể ngắn hơn ``lo``.
    """
    f_lo = difference(lo)
    f_hi = difference(hi)
    valid = np.isfinite(f_lo) & np.isfinite(f_hi) & (np.sign(f_lo) * np.sign(f_hi) < 0)
    lo, hi, f_lo = lo[valid], hi[valid], f_lo[valid]
    for _ in range(_BISECTION_STEPS):
        mid = 0.5 * (lo + hi)
        f_mid = difference(mid)
        finite = np.isfinite(f_mid)
        lo, hi, mid, f_mid, f_lo = lo[finite], hi[finite], mid[finite], f_mid[finite], f_lo[finite]
        same_side = np.sign(f_mid) == np.sign(f_lo)
        lo = np.where(same_side, mid, lo)
        f_lo = np.where(same_side, f_mid, f_lo)
        hi = np.where(same_side, hi, mid)
    return 0.5 * (lo + hi)


def _difference_function(f: ParsedFunction, g: ParsedFunction) -> Callable[[float], float]:
    """Trả về hàm vô hướng ``t -> f(t) - g(t)`` để đưa vào ``brentq``.

    Args:
        f: Hàm thứ nhất.
        g: Hàm thứ hai.

    Returns:
        Hàm nhận một số thực, trả về hiệu hai hàm. Trả về ``NaN`` nếu một trong hai không xác định.
    """

    def difference(t: float) -> float:
        """Hiệu ``f(t) - g(t)`` tại một điểm."""
        point = np.array([t])
        return float(f(point)[0] - g(point)[0])

    return difference


def _abs_difference_function(difference: Callable[[float], float]) -> Callable[[float], float]:
    """Trả về ``t -> |h(t)|`` từ hàm hiệu ``h``, để tìm cực tiểu."""

    def absolute(t: float) -> float:
        """Giá trị tuyệt đối của hiệu tại một điểm. ``NaN`` được coi là ``+inf`` khi so sánh."""
        value = difference(t)
        return float("inf") if np.isnan(value) else abs(value)

    return absolute


def _verified_roots(
    candidates: list[float],
    f: ParsedFunction,
    g: ParsedFunction,
    x_min: float,
    x_max: float,
) -> list[Intersection]:
    """Giữ ứng viên mà ``|f - g|`` thật sự xấp xỉ 0, rồi gộp trùng và tính tung độ.

    Args:
        candidates: Hoành độ ứng viên, có thể trùng nhau hoặc nằm ngoài khoảng.
        f: Hàm dùng để tính tung độ.
        g: Hàm thứ hai, dùng để kiểm tra nghiệm.
        x_min: Cận dưới của khoảng.
        x_max: Cận trên của khoảng.

    Returns:
        Danh sách ``Intersection`` đã sắp xếp theo ``x``.
    """
    roots = np.asarray(candidates, dtype=float)
    roots = roots[(roots >= x_min) & (roots <= x_max)]
    if roots.size == 0:
        return []
    f_roots = f(roots)
    g_roots = g(roots)
    tolerance = _RELATIVE_TOLERANCE * np.maximum(1.0, np.maximum(np.abs(f_roots), np.abs(g_roots)))
    roots = roots[np.abs(f_roots - g_roots) <= tolerance]
    if roots.size == 0:
        return []
    return _deduplicate(roots, f, x_min, x_max)


def _check_range(x_min: float, x_max: float, samples: int) -> None:
    """Kiểm tra tham số miền và số mẫu.

    Raises:
        ValueError: Khi ``x_min >= x_max`` hoặc ``samples < 2``.
    """
    if x_min >= x_max:
        raise ValueError("x_min phải nhỏ hơn x_max.")
    if samples < 2:
        raise ValueError("samples phải lớn hơn hoặc bằng 2.")


def _max_abs(*arrays: np.ndarray) -> float:
    """Trả về giá trị tuyệt đối lớn nhất trong các mảng, bỏ qua ``NaN``, hoặc 0 nếu rỗng."""
    values = [np.abs(a[np.isfinite(a)]) for a in arrays]
    merged = np.concatenate(values) if values else np.empty(0)
    return float(merged.max()) if merged.size else 0.0


def _local_minima(values: np.ndarray) -> np.ndarray:
    """Tìm chỉ số các cực tiểu địa phương (bao gồm hai đầu mút) của mảng ``values``.

    Điểm ``NaN`` không bao giờ được coi là cực tiểu.

    Args:
        values: Mảng không âm, có thể chứa ``NaN``.

    Returns:
        Mảng chỉ số nguyên đã sắp xếp.
    """
    left = np.concatenate(([np.inf], values[:-1]))
    right = np.concatenate((values[1:], [np.inf]))
    # Dùng "<" ở phía phải: đoạn phẳng (|h| không đổi, ví dụ x + 1 so với |x| - 2 với x ≥ 0) chỉ
    # cho một cực tiểu ở cuối đoạn, thay vì mọi điểm trên đoạn đều thành cực tiểu.
    with np.errstate(invalid="ignore"):
        mask = np.isfinite(values) & (values <= left) & (values < right)
    return np.flatnonzero(mask)


def _deduplicate(roots: np.ndarray, f: ParsedFunction, x_min: float, x_max: float) -> list[Intersection]:
    """Sắp xếp nghiệm, gộp các nghiệm gần nhau và tính tung độ.

    Args:
        roots: Mảng hoành độ nghiệm, chưa sắp xếp, có thể trùng nhau.
        f: Hàm dùng để tính tung độ.
        x_min: Cận dưới của miền dò, dùng để xác định ngưỡng gộp.
        x_max: Cận trên của miền dò.

    Returns:
        Danh sách ``Intersection`` đã sắp xếp theo ``x``.
    """
    # Ngưỡng gộp: một phần triệu độ rộng miền, đủ nhỏ để không gộp hai giao điểm thật.
    min_gap = _DEDUP_RELATIVE_GAP * (x_max - x_min)
    unique: list[float] = []
    for r in np.sort(roots):
        if not unique or r - unique[-1] > min_gap:
            unique.append(float(r))
    result: list[Intersection] = []
    for x in unique:
        # Nghiệm như 3.9e-21 thay vì 0 là sai số float; làm tròn về 0 để nhãn hiển thị đẹp.
        x = 0.0 if abs(x) < _ZERO_SNAP else x
        y = float(f(np.array([x]))[0])
        y = 0.0 if abs(y) < _ZERO_SNAP else y
        if np.isfinite(y):
            result.append(Intersection(x=x, y=y))
    return result
