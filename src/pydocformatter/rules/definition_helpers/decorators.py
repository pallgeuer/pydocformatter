"""Decorator name extraction helpers."""

from __future__ import annotations

import libcst as cst


def decorator_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted decorator name, unwrapping direct decorator calls.

    Args:
        expression (cst.BaseExpression): Decorator expression or call expression to inspect.

    Returns:
        str | None: Dotted name such as `abc.abstractmethod`, or None for dynamic decorator expressions.
    """
    if isinstance(expression, cst.Call):
        return _static_qualified_name(expression.func)
    return _static_qualified_name(expression)


def _static_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted static expression name."""
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = _static_qualified_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None
