"""Static exception-name extraction helpers."""

# Future imports
from __future__ import annotations

# Third-party imports
import libcst as cst


def exception_name(expression: cst.BaseExpression | None) -> str | None:
    """Return a statically comparable raised exception name, if one is present.

    Args:
        expression (cst.BaseExpression | None): Raised expression or call target to inspect.

    Returns:
        str | None: Comparable exception name, or None when the expression is dynamic or not exception-like.
    """
    if expression is None:
        return None
    if isinstance(expression, cst.Call):
        return exception_name(expression.func)
    if isinstance(expression, cst.Name):
        return expression.value if _looks_like_exception_name(expression.value) else None
    if isinstance(expression, cst.Attribute):
        parent = _exception_name_parent(expression.value)
        if parent is None:
            return expression.attr.value if _looks_like_exception_name(expression.attr.value) else None
        return f"{parent}.{expression.attr.value}" if _looks_like_exception_name(expression.attr.value) else None
    return None


def _looks_like_exception_name(name: str) -> bool:
    """Return whether a name follows the direct exception-name heuristic."""
    # Static-only heuristic: direct capitalized names are comparable, while dynamic/lowercase aliases are intentionally
    # ignored.
    return bool(name) and name[0].isupper()


def _exception_name_parent(expression: cst.BaseExpression) -> str | None:
    """Return the dotted parent prefix for a raised exception attribute expression."""
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = _exception_name_parent(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None
