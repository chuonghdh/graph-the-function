"""Unit test cho ``graph_app.equations``: tự nhận diện loại, chiều và lỗi cú pháp."""

from __future__ import annotations

import numpy as np
import pytest

from graph_app.equations import detect_dimension, parse_all_equations, parse_user_equation
from graph_app.math_engine import ExpressionError


class TestKindAndDimension:
    """Mỗi dạng nhập được phân loại đúng loại và chiều."""

    @pytest.mark.parametrize("text", ["sin(x)", "x^2 - 2", "  2x + 1  ", "3"])
    def test_bare_expression_is_explicit_y_2d(self, text: str) -> None:
        """Biểu thức không có dấu ``=``, không chứa y hay z, được hiểu là y = f(x)."""
        eq = parse_user_equation(text)
        assert eq.kind == "explicit_y"
        assert eq.dimension == "2d"
        assert eq.func.variables == ("x",)

    @pytest.mark.parametrize(
        ("text", "x", "expected"),
        [("y = x**2 + 2*x + 1", 2.0, 9.0), ("y = sin(x)", 0.0, 0.0)],
    )
    def test_y_equals_function_is_explicit_y(self, text: str, x: float, expected: float) -> None:
        """``y = g(x)`` được nhận là explicit_y và hàm vẽ là ``g``."""
        eq = parse_user_equation(text)
        assert eq.kind == "explicit_y"
        assert eq.func(x) == pytest.approx(expected)

    def test_z_equals_function_is_explicit_z_3d(self) -> None:
        """``z = f(x, y)`` là mặt 3D tường minh."""
        eq = parse_user_equation("z = x**2 + y**2")
        assert eq.kind == "explicit_z"
        assert eq.dimension == "3d"
        assert eq.func(3.0, 4.0) == pytest.approx(25.0)
        assert eq.implicit_2d is None

    @pytest.mark.parametrize(
        ("text", "dimension"),
        [
            ("x**2 + y**2 = 25", "2d"),
            ("x^2/9 + y^2/4 = 1", "2d"),
            ("sin(x) = cos(y)", "2d"),
            ("x**2 + y**2 - 25", "2d"),
            ("x = 2", "2d"),
            ("x**2 + y**2 + z**2 = 16", "3d"),
            ("y = z", "3d"),
            ("z", "3d"),
        ],
    )
    def test_implicit_dimension_follows_variables(self, text: str, dimension: str) -> None:
        """Chiều của phương trình ẩn phụ thuộc vào việc nó có chứa z hay không."""
        eq = parse_user_equation(text)
        assert eq.kind == "implicit"
        assert eq.dimension == dimension

    def test_implicit_form_is_lhs_minus_rhs(self) -> None:
        """``F = A − B`` nên điểm nằm trên đường thì F = 0."""
        eq = parse_user_equation("x**2 + y**2 = 25")
        assert eq.implicit_2d is not None
        assert eq.implicit_2d(3.0, 4.0) == pytest.approx(0.0)

    def test_explicit_y_has_implicit_form_y_minus_g(self) -> None:
        """``y = x^2`` có dạng ẩn ``y − x^2``, để so sánh được với đường ẩn khác."""
        eq = parse_user_equation("y = x^2")
        assert eq.implicit_2d is not None
        assert eq.implicit_2d(2.0, 4.0) == pytest.approx(0.0)
        assert eq.implicit_2d(2.0, 5.0) == pytest.approx(1.0)

    def test_explicit_y_has_3d_implicit_form_for_extrusion(self) -> None:
        """``y = g(x)`` vẫn có dạng 3D ``y − g(x)``, để vẽ thành mặt trụ đứng trong chế độ 3D."""
        eq = parse_user_equation("y = x^2")
        values = eq.implicit_3d(np.array([2.0]), np.array([4.0]), np.array([99.0]))
        assert values[0] == pytest.approx(0.0)


class TestErrors:
    """Lỗi cú pháp được báo bằng tiếng Việt, kèm gợi ý khi đoán được ý người dùng."""

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("x <= 2", "Bất đẳng thức"),
            ("x == 2", "Bất đẳng thức"),
            ("x = y = 2", "đúng một dấu"),
            ("= x^2", "Thiếu vế"),
            ("x^2 =", "Thiếu vế"),
        ],
    )
    def test_invalid_relations_are_rejected(self, text: str, message: str) -> None:
        """Bất đẳng thức, nhiều dấu bằng và vế trống bị từ chối."""
        with pytest.raises(ExpressionError, match=message):
            parse_user_equation(text)

    def test_unknown_variable_is_rejected(self) -> None:
        """Biến ngoài x, y, z bị từ chối."""
        with pytest.raises(ExpressionError, match="w"):
            parse_user_equation("x^2 + w^2 = 1")

    def test_missing_multiplication_hint(self) -> None:
        """``xy`` đưa ra gợi ý viết ``x*y``."""
        with pytest.raises(ExpressionError, match=r"x\*y"):
            parse_user_equation("xy = 1")

    def test_missing_power_hint(self) -> None:
        """``x2`` đưa ra gợi ý viết ``x^2``."""
        with pytest.raises(ExpressionError, match=r"x\^2"):
            parse_user_equation("x2 + y2 = 1")


class TestBatchParsing:
    """Phân tích nhiều ô và nhận diện chiều của cả hệ thống."""

    def test_errors_name_the_failing_box(self) -> None:
        """Mỗi lỗi mở đầu bằng đúng tên ô, để người dùng biết ô nào cần sửa."""
        texts = ["sin(x)", "x <= 2", ""]
        equations, errors = parse_all_equations(texts)
        assert set(equations) == {0}
        assert len(errors) == 1
        assert errors[0].startswith("**f2**")

    def test_empty_boxes_are_skipped(self) -> None:
        """Ô rỗng không tạo phương trình và không tạo lỗi."""
        equations, errors = parse_all_equations(["", "   ", ""])
        assert equations == {}
        assert errors == []

    def test_one_z_function_switches_whole_scene_to_3d(self) -> None:
        """Chỉ cần một ô có z, cả hệ thống chuyển sang 3D, dù các ô khác là 2D."""
        texts = ["x^2 - 2", "sin(x)", "z = x*y"]
        equations, _ = parse_all_equations(texts)
        assert detect_dimension(equations, texts) == "3d"

    def test_only_xy_functions_stay_2d(self) -> None:
        """Nếu không ô nào chứa z, hệ thống ở 2D."""
        texts = ["x^2 + y^2 = 25", "sin(x) = cos(y)", "y = x"]
        equations, _ = parse_all_equations(texts)
        assert detect_dimension(equations, texts) == "2d"

    def test_z_in_broken_box_still_selects_3d(self) -> None:
        """Ô có z nhưng lỗi cú pháp vẫn đưa hệ thống về 3D, để lỗi hiện đúng ngữ cảnh."""
        texts = ["x^2", "z = x**2 + ", ""]
        equations, errors = parse_all_equations(texts)
        assert errors
        assert detect_dimension(equations, texts) == "3d"

    def test_empty_input_is_2d(self) -> None:
        """Không có gì nhập thì mặc định 2D."""
        assert detect_dimension({}, ["", "", ""]) == "2d"
