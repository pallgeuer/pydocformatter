"""Suppression-selector representation policies shared by PCF008 and PCF009."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.rules.definition_helpers import directives


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.models import RuleMetadata


def violations(context: RuleContext, *, rule: RuleMetadata, prefer_names: bool) -> tuple[rule_violations.RuleViolation, ...]:
    """Return one representation-policy violation per affected bracket directive.

    Args:
        context (RuleContext): Current file context with shared parsed PCF directives.
        rule (RuleMetadata): Policy rule metadata attached to returned findings.
        prefer_names (bool): Whether exact pydocfmt codes and Ruff code-shaped tokens are violations.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: Fixable local findings and diagnostic-only Ruff findings.
    """
    data = PCF_definition.PCF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for directive in data.bracket_directives:
        if directive.tool is directives.DirectiveTool.PYDOCFMT:
            if directive.action not in {"ignore", "file-ignore"}:
                continue
            violation = _pydocfmt_violation(directive, rule=rule, prefer_names=prefer_names)
            if violation is not None:
                results.append(violation)
        elif _ruff_directive_violates(directive, prefer_names=prefer_names):
            results.append(rule_violations.diagnostic(rule, (_directive_line(directive),)))
    return tuple(results)


def _pydocfmt_violation(directive: directives.BracketDirective, *, rule: RuleMetadata, prefer_names: bool) -> rule_violations.RuleViolation | None:
    """Return a fixable local policy violation for one directive when needed."""
    offending_kind = directives.DirectiveTokenKind.PYDOCFMT_EXACT_CODE if prefer_names else directives.DirectiveTokenKind.PYDOCFMT_EXACT_NAME
    if not any(token.kind is offending_kind for token in directive.tokens):
        return None
    replacements: dict[int, str] = {}
    for token in directive.tokens:
        if token.kind is not offending_kind:
            continue
        replacement = token.resolved_name if prefer_names else (token.resolved_code.tag if token.resolved_code is not None else None)
        if replacement is None:
            raise AssertionError("Exact pydocfmt policy token must resolve to canonical code and name spellings")
        replacements[token.source_order] = replacement
    if directive.selectors_range is None:
        raise ValueError("Pydocfmt policy directive must have selector-list source bounds")
    line = _directive_line(directive)
    change = rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=directive.selectors_range, replacement=directive.targeted_selectors(replacements)), line_numbers=(line,), suppression_line_numbers=()
    )
    return rule_violations.violation_for_planned_source_change(rule, change)


def _ruff_directive_violates(directive: directives.BracketDirective, *, prefer_names: bool) -> bool:
    """Return whether a recognized Ruff directive contains a disallowed token shape."""
    offending_kind = directives.DirectiveTokenKind.RUFF_EXACT_CODE if prefer_names else directives.DirectiveTokenKind.RUFF_NAME
    return directive.action in {"ignore", "file-ignore", "disable", "enable"} and any(token.kind is offending_kind for token in directive.tokens)


def _directive_line(directive: directives.BracketDirective) -> int:
    """Return the physical source line of a prepared directive."""
    if directive.comment_range is None:
        raise ValueError("Prepared directive must have comment source bounds")
    return directive.comment_range.start.line
