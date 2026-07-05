"""Static expression-name matching helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

import libcst as cst
import libcst.metadata as cst_metadata

from pydocformatter.rules.definition import RuleCategoryContext

_ALIAS_MATCH_SOURCES = frozenset((cst_metadata.QualifiedNameSource.IMPORT, cst_metadata.QualifiedNameSource.BUILTIN))


def expression_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted static expression name.

    Args:
        expression (cst.BaseExpression): Expression to inspect.

    Returns:
        Dotted name for static name and attribute expressions, or None for dynamic expressions.
    """
    if isinstance(expression, cst.Name):
        return expression.value
    if isinstance(expression, cst.Attribute):
        parent = expression_name(expression.value)
        if parent is None:
            return None
        return f"{parent}.{expression.attr.value}"
    return None


def configured_expression_name(expression: cst.BaseExpression, configured_names: tuple[str, ...], *, context: RuleCategoryContext, unwrap_call: bool = False) -> str | None:
    """Return the source expression name when it matches configured names.

    Args:
        expression (cst.BaseExpression): Expression to compare.
        configured_names (tuple[str, ...]): Exact syntactic names and qualified import/builtin names accepted as
            matches.
        context (RuleCategoryContext): Current source context used for LibCST qualified-name metadata.
        unwrap_call (bool): Whether to compare direct call functions instead of the whole expression.

    Returns:
        Source spelling of the static expression name when matched, or None when no safe static match exists.
    """
    inspected = expression.func if unwrap_call and isinstance(expression, cst.Call) else expression
    source_name = expression_name(inspected)
    if source_name is None:
        return None
    if "." not in source_name and source_name in configured_names:
        return source_name
    qualified_configured_names = frozenset(name for name in configured_names if "." in name)
    if not qualified_configured_names:
        return None
    qualified_names = _qualified_names(inspected, context=context)
    if any(qualified_name.source is cst_metadata.QualifiedNameSource.LOCAL for qualified_name in qualified_names):
        return None
    if source_name in qualified_configured_names:
        return source_name
    for qualified_name in qualified_names:
        if qualified_name.source in _ALIAS_MATCH_SOURCES and qualified_name.name in qualified_configured_names:
            return source_name
    return None


def configured_expression_matches(expression: cst.BaseExpression, configured_names: tuple[str, ...], *, context: RuleCategoryContext) -> bool:
    """Return whether an expression matches configured names syntactically or through safe qualified metadata.

    Args:
        expression (cst.BaseExpression): Expression to compare.
        configured_names (tuple[str, ...]): Exact syntactic names and qualified import/builtin names accepted as
            matches.
        context (RuleCategoryContext): Current source context used for LibCST qualified-name metadata.

    Returns:
        bool: Whether the expression is a safe match.
    """
    return configured_expression_name(expression, configured_names, context=context) is not None


def _qualified_names(expression: cst.BaseExpression, *, context: RuleCategoryContext) -> tuple[cst_metadata.QualifiedName, ...]:
    """Return LibCST qualified names for an expression."""
    qualified_name_map = context.metadata_wrapper.resolve(cst_metadata.QualifiedNameProvider)
    try:
        qualified_names = qualified_name_map[expression]
    except KeyError:
        return ()
    if callable(qualified_names):
        qualified_names = qualified_names()
    return tuple(cast(Iterable[cst_metadata.QualifiedName], qualified_names))
