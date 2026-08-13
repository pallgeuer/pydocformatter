"""Static expression-name matching helpers."""

# Future imports
from __future__ import annotations

# Standard library imports
import enum
import typing
from collections.abc import Iterable
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.definition_helpers import module_bindings


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleCategoryContext


_ALIAS_MATCH_SOURCES = frozenset((cst_metadata.QualifiedNameSource.IMPORT, cst_metadata.QualifiedNameSource.BUILTIN))
_CANONICAL_QUALIFIED_ROOTS = frozenset(("abc", "builtins", "collections", "enum", "functools", "types", "typing", "typing_extensions"))


def expression_name(expression: cst.BaseExpression) -> str | None:
    """Return a dotted static expression name.

    Args:
        expression (cst.BaseExpression): Expression to inspect.

    Returns:
        Dotted name for static name and attribute expressions, or None for dynamic expressions.
    """
    return module_bindings.expression_name(expression)


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
    module_match = _module_binding_match(inspected, source_name, qualified_configured_names, context=context)
    if module_match is _StaticMatch.MATCH:
        if (
            _match_needs_metadata_guard(source_name, context=context)
            and _metadata_match(_qualified_names(inspected, context=context), qualified_configured_names) is _StaticMatch.NO_MATCH
            and not _is_explicit_noncanonical_exact_match(source_name, qualified_configured_names)
        ):
            return None
        return source_name
    if module_match is _StaticMatch.NO_MATCH:
        return None
    qualified_names = _qualified_names(inspected, context=context)
    metadata_match = _metadata_match(qualified_names, qualified_configured_names)
    if metadata_match is _StaticMatch.MATCH:
        return source_name
    if metadata_match is _StaticMatch.NO_MATCH:
        if _is_explicit_noncanonical_exact_match(source_name, qualified_configured_names):
            return source_name
        return None
    if source_name in qualified_configured_names:
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
        qualified_names = typing.cast("typing.Callable[[], Iterable[cst_metadata.QualifiedName]]", qualified_names)()
    return tuple(qualified_names)


def _metadata_match(qualified_names: tuple[cst_metadata.QualifiedName, ...], qualified_configured_names: frozenset[str]) -> _StaticMatch:
    """Return a LibCST metadata match decision for qualified configured names."""
    if any(qualified_name.source in _ALIAS_MATCH_SOURCES and qualified_name.name in qualified_configured_names for qualified_name in qualified_names):
        return _StaticMatch.MATCH
    if any(qualified_name.source in _ALIAS_MATCH_SOURCES for qualified_name in qualified_names):
        return _StaticMatch.NO_MATCH
    if any(qualified_name.source is cst_metadata.QualifiedNameSource.LOCAL for qualified_name in qualified_names):
        return _StaticMatch.NO_MATCH
    return _StaticMatch.UNKNOWN


def _is_explicit_noncanonical_exact_match(source_name: str, qualified_configured_names: frozenset[str]) -> bool:
    """Return whether a configured dotted name is best treated as a user alias spelling."""
    source_root = source_name.split(".", 1)[0]
    return source_name in qualified_configured_names and source_root not in _CANONICAL_QUALIFIED_ROOTS


def _module_binding_match(expression: cst.BaseExpression, source_name: str, qualified_configured_names: frozenset[str], *, context: RuleCategoryContext) -> _StaticMatch:
    """Return a conservative module-syntax match decision for a qualified configured name."""
    source_root = source_name.split(".", 1)[0]
    use_key = _expression_key(expression, context=context)
    if use_key is None:
        return _StaticMatch.UNKNOWN
    bindings = _module_bindings(context)
    binding = bindings.binding_at(source_root, use_key)
    if binding is not None and binding.kind is module_bindings.BindingKind.UNKNOWN:
        return _StaticMatch.UNKNOWN
    if source_name in qualified_configured_names:
        if binding is None:
            return _StaticMatch.UNKNOWN if bindings.has_uncertain_import_root(source_root) else _StaticMatch.MATCH
        if binding.kind is module_bindings.BindingKind.LOCAL:
            return _StaticMatch.NO_MATCH
        imported_name = binding.qualified_name
        if imported_name is None:
            return _StaticMatch.UNKNOWN
        resolved_source_name = imported_name if source_name == source_root else f"{imported_name}.{source_name.split('.', 1)[1]}"
        if resolved_source_name not in qualified_configured_names and source_root not in _CANONICAL_QUALIFIED_ROOTS:
            return _StaticMatch.MATCH
        return _StaticMatch.MATCH if resolved_source_name in qualified_configured_names else _StaticMatch.NO_MATCH
    if f"builtins.{source_name}" in qualified_configured_names and "." not in source_name and binding is None:
        return _StaticMatch.UNKNOWN if bindings.has_uncertain_import_root(source_root) else _StaticMatch.MATCH
    if binding is None:
        return _StaticMatch.UNKNOWN if bindings.has_uncertain_import_root(source_root) else _StaticMatch.NO_MATCH
    if binding.kind is module_bindings.BindingKind.LOCAL:
        return _StaticMatch.NO_MATCH
    imported_name = binding.qualified_name
    if imported_name is None:
        return _StaticMatch.UNKNOWN
    resolved_source_name = imported_name if source_name == source_root else f"{imported_name}.{source_name.split('.', 1)[1]}"
    return _StaticMatch.MATCH if resolved_source_name in qualified_configured_names else _StaticMatch.NO_MATCH


def _match_needs_metadata_guard(source_name: str, *, context: RuleCategoryContext) -> bool:
    """Return whether a fast-path match needs LibCST metadata confirmation."""
    source_root = source_name.split(".", 1)[0]
    bindings = _module_bindings(context)
    return bindings.has_uncertain_import_root(source_root) or bindings.has_uncertain_local_root(source_root)


def _module_bindings(context: RuleCategoryContext) -> module_bindings.ModuleBindings:
    """Return top-level bindings that affect configured static-name matching."""
    prepared_bindings = _prepared_module_bindings(context)
    if prepared_bindings is not None:
        return prepared_bindings
    return module_bindings.collect_top_level_bindings(context.module, positions=context.positions)


def _prepared_module_bindings(context: RuleCategoryContext) -> module_bindings.ModuleBindings | None:
    """Return cached PDF category bindings when the context carries prepared PDF data."""
    if not isinstance(context, RuleContext):
        return None
    # First-party imports
    import pydocformatter.rules.definitions.PDF.PDF as PDF_definition  # ruff: ignore[import-outside-top-level]

    try:
        data = PDF_definition.PDF.require_data(context)
    except TypeError:
        return None
    bindings = data._module_bindings
    if bindings is not None:
        return bindings
    bindings = module_bindings.collect_top_level_bindings(context.module, positions=context.positions)
    object.__setattr__(data, "_module_bindings", bindings)
    return bindings


def _expression_key(expression: cst.BaseExpression, *, context: RuleCategoryContext) -> tuple[int, int] | None:
    """Return a comparable source-position key for one expression."""
    position = context.positions.get(expression)
    if position is None:
        return None
    return module_bindings.position_key(position.start)


class _StaticMatch(enum.Enum):
    """Conservative match states before falling back to LibCST metadata."""

    MATCH = "match"
    NO_MATCH = "no-match"
    UNKNOWN = "unknown"
