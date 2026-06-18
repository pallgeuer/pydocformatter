from __future__ import annotations

import libcst as cst


def decorator_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted decorator name, unwrapping decorator calls."""
    if isinstance(expression, cst.Call):
        return decorator_qualified_name(expression.func)
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = decorator_qualified_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None
