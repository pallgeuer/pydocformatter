"""Test adapters for direct rule API calls."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.runner as rule_runner
from pydocformatter.rules.models import RuleFinding


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleBase, RuleContext


@dataclasses.dataclass(frozen=True)
class DirectRuleFixOutcome:
    """Applied source-fix view used by focused rule tests.

    Attributes:
        module (cst.Module): Parsed module after direct rule fixes have been applied.
        fixed_findings (tuple[RuleFinding, ...]): Findings associated with the violations whose source fixes were
            applied.
    """

    module: cst.Module
    fixed_findings: tuple[RuleFinding, ...] = ()


def rule_findings(rule_class: type[RuleBase], context: RuleContext) -> tuple[RuleFinding, ...]:
    """Return findings from a rule's canonical violations.

    Args:
        rule_class (type[RuleBase]): Rule implementation to execute through the same validation path used by direct rule
            tests.
        context (RuleContext): Prepared rule context containing parsed source and any category data required by the
            rule.

    Returns:
        Public findings derived from the rule's validated violations.
    """
    return tuple(violation.finding for violation in validated_rule_violations(rule_class, context))


def rule_fix_result(rule_class: type[RuleBase], context: RuleContext) -> DirectRuleFixOutcome:
    """Apply unsuppressed source fixes from a rule's canonical violations.

    Args:
        rule_class (type[RuleBase]): Rule implementation whose fixable violations should be applied directly.
        context (RuleContext): Prepared rule context for the source module under test.

    Returns:
        Parsed module after applying all available direct rule fixes, together with the findings that were fixed.

    Raises:
        AssertionError: Raised when the rule runner rejects the planned source changes or reports validation errors.
    """
    fixable_violations = tuple(violation for violation in validated_rule_violations(rule_class, context) if violation.fix is not None)
    if not fixable_violations:
        return DirectRuleFixOutcome(module=context.module)
    errors: list[str] = []
    changes = rule_runner._planned_source_changes_for_violations(rule_class, fixable_violations, path=context.path, source_line_count=len(context.source_lines), errors=errors)
    if errors or changes is None:
        raise AssertionError("; ".join(errors) or "Direct rule test source-fix validation failed")
    return DirectRuleFixOutcome(module=rule_edits.apply_context_source_changes(context, changes), fixed_findings=tuple(violation.finding for violation in fixable_violations))


def validated_rule_violations(rule_class: type[RuleBase], context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations after applying runner validation used by direct rule tests.

    Args:
        rule_class (type[RuleBase]): Rule implementation whose raw violations should be validated.
        context (RuleContext): Prepared rule context used to call the rule's violations hook.

    Returns:
        Validated rule violations in the order produced by the rule implementation.

    Raises:
        AssertionError: Raised when runner validation reports malformed violations.
    """
    errors: list[str] = []
    violations = rule_runner._validated_rule_violations(
        rule_class, rule_class.violations(context), path=context.path, operation="direct rule test", source_line_count=len(context.source_lines), errors=errors
    )
    if errors:
        raise AssertionError("; ".join(errors))
    return violations
