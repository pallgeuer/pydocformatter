"""Decorator name extraction helpers."""

from __future__ import annotations

import libcst as cst

from pydocformatter.cli.settings_check import CheckSettings


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


def has_property_decorator(decorators: tuple[cst.Decorator, ...], *, settings: CheckSettings) -> bool:
    """Return whether decorators identify a property-like function.

    Args:
        decorators (tuple[cst.Decorator, ...]): Function decorators to inspect.
        settings (CheckSettings): Resolved settings containing exact property decorator names.

    Returns:
        bool: Whether any decorator matches configured property decorators or a property accessor suffix.
    """
    return any((decorator_name := decorator_qualified_name(decorator.decorator)) is not None and is_property_decorator_name(decorator_name, settings=settings) for decorator in decorators)


def is_property_decorator_name(decorator_name: str, *, settings: CheckSettings) -> bool:
    """Return whether a decorator name identifies a property-like decorator.

    Args:
        decorator_name (str): Dotted decorator name after direct call unwrapping.
        settings (CheckSettings): Resolved settings containing exact property decorator names.

    Returns:
        bool: Whether the name exactly matches configured property decorators or a property accessor suffix.
    """
    parent, _, accessor = decorator_name.rpartition(".")
    return decorator_name in settings.docstring_property_decorators or (bool(parent) and accessor in _PROPERTY_ACCESSOR_DECORATOR_NAMES)


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


_PROPERTY_ACCESSOR_DECORATOR_NAMES = {"getter", "setter", "deleter"}
