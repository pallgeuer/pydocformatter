"""Decorator name extraction helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
from pydocformatter.rules.definition_helpers import static_names


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.definition import RuleCategoryContext


def decorator_qualified_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted decorator name, unwrapping direct decorator calls.

    Args:
        expression (cst.BaseExpression): Decorator expression or call expression to inspect.

    Returns:
        str | None: Dotted name such as `abc.abstractmethod`, or None for dynamic decorator expressions.
    """
    if isinstance(expression, cst.Call):
        return static_names.expression_name(expression.func)
    return static_names.expression_name(expression)


def matched_property_decorator_name(decorator: cst.Decorator, *, context: RuleCategoryContext, settings: CheckSettings) -> str | None:
    """Return a property-like decorator source name when the decorator matches.

    Args:
        decorator (cst.Decorator): Decorator to inspect.
        context (RuleCategoryContext): Current source context used for import-aware matching.
        settings (CheckSettings): Resolved settings containing exact property decorator names.

    Returns:
        Matched decorator source name, or None when the decorator is not property-like.
    """
    decorator_name = static_names.configured_expression_name(decorator.decorator, settings.docstring_property_decorators, context=context, unwrap_call=True)
    if decorator_name is not None:
        return decorator_name
    source_name = decorator_qualified_name(decorator.decorator)
    if source_name is None or not is_property_accessor_decorator_name(source_name):
        return None
    return source_name


def has_property_decorator(decorators: tuple[cst.Decorator, ...], *, context: RuleCategoryContext, settings: CheckSettings) -> bool:
    """Return whether decorators identify a property-like function.

    Args:
        decorators (tuple[cst.Decorator, ...]): Function decorators to inspect.
        context (RuleCategoryContext): Current source context used for import-aware matching.
        settings (CheckSettings): Resolved settings containing exact property decorator names.

    Returns:
        bool: Whether any decorator matches configured property decorators or a property accessor suffix.
    """
    return any(matched_property_decorator_name(decorator, context=context, settings=settings) is not None for decorator in decorators)


def is_property_accessor_decorator_name(decorator_name: str) -> bool:
    """Return whether a decorator source name is a property accessor.

    Args:
        decorator_name (str): Dotted decorator name after direct call unwrapping.

    Returns:
        bool: Whether the name has a parent and a property accessor suffix.
    """
    parent, _, accessor = decorator_name.rpartition(".")
    return bool(parent) and accessor in _PROPERTY_ACCESSOR_DECORATOR_NAMES


_PROPERTY_ACCESSOR_DECORATOR_NAMES = {"getter", "setter", "deleter"}
