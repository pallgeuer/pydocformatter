"""Test adapters for direct rule API calls."""

from __future__ import annotations

import dataclasses

import libcst as cst

import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.runner as rule_runner
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import RuleFinding


@dataclasses.dataclass(frozen=True)
class DirectRuleFixOutcome:
    """Applied source-fix view used by focused rule tests."""

    module: cst.Module
    fixed_findings: tuple[RuleFinding, ...] = ()


def rule_findings(rule_class: type[RuleBase], context: RuleContext) -> tuple[RuleFinding, ...]:
    """Return findings from a rule's canonical violations."""
    return tuple(violation.finding for violation in validated_rule_violations(rule_class, context))


def rule_fix_result(rule_class: type[RuleBase], context: RuleContext) -> DirectRuleFixOutcome:
    """Apply unsuppressed source fixes from a rule's canonical violations."""
    fixable_violations = tuple(violation for violation in validated_rule_violations(rule_class, context) if violation.fix is not None)
    if not fixable_violations:
        return DirectRuleFixOutcome(module=context.module)
    errors: list[str] = []
    changes = rule_runner._planned_source_changes_for_violations(rule_class, fixable_violations, path=context.path, source_line_count=len(context.source_lines), errors=errors)
    if errors or changes is None:
        raise AssertionError("; ".join(errors) or "Direct rule test source-fix validation failed")
    return DirectRuleFixOutcome(module=rule_edits.apply_context_source_changes(context, changes), fixed_findings=tuple(violation.finding for violation in fixable_violations))


def validated_rule_violations(rule_class: type[RuleBase], context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations after applying runner validation used by direct rule tests."""
    errors: list[str] = []
    violations = rule_runner._validated_rule_violations(
        rule_class, rule_class.violations(context), path=context.path, operation="direct rule test", source_line_count=len(context.source_lines), errors=errors
    )
    if errors:
        raise AssertionError("; ".join(errors))
    return violations
