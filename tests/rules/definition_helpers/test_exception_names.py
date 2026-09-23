"""Tests for static exception-name extraction."""

# Third-party imports
import libcst as cst
import pytest

# First-party imports
from pydocformatter.rules.definition_helpers import exception_names


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("RuntimeError", "RuntimeError"),
        ("RuntimeError()", "RuntimeError"),
        ("package.errors.CustomError", "package.errors.CustomError"),
        ("package.errors.CustomError()", "package.errors.CustomError"),
        ("lowercase_error", None),
        ("package.errors.not_an_error", None),
        ("build_error()", None),
        ("errors[code]", None),
    ],
)
def test_exception_name_extracts_only_statically_comparable_names(expression: str, expected: str | None) -> None:
    """Accept direct exception-like names and reject dynamic or lowercase expressions."""
    assert exception_names.exception_name(cst.parse_expression(expression)) == expected


@pytest.mark.parametrize(
    ("expression", "expected"), [("factory().CustomError", "CustomError"), ("factory().not_an_error", None), ("factory().errors.CustomError", "CustomError"), ("factory().errors.not_an_error", None)]
)
def test_exception_name_conservatively_falls_back_after_dynamic_parents(expression: str, expected: str | None) -> None:
    """Keep a comparable final exception name without claiming a dynamic qualification."""
    assert exception_names.exception_name(cst.parse_expression(expression)) == expected


def test_exception_name_accepts_an_absent_raise_expression() -> None:
    """A bare raise has no new statically comparable exception name."""
    assert exception_names.exception_name(None) is None
