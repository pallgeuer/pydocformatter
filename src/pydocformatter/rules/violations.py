"""Internal rule violation and source-fix records."""

from __future__ import annotations

import dataclasses

import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.line_targets as line_targets
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class RuleSourceFix:
    """Source-edit plan for one fixable rule violation.

    Attributes:
        _change (rule_edits.PlannedSourceChange): Source change for this fix.
    """

    _change: rule_edits.PlannedSourceChange = dataclasses.field(repr=False)

    def __post_init__(self) -> None:
        """Validate the source change backing this fix."""
        _validate_planned_change(self._change)

    @classmethod
    def from_change(cls, change: rule_edits.PlannedSourceChange) -> RuleSourceFix:
        """Return a source fix backed by one already-planned source change."""
        return cls(change)

    def planned_changes(self) -> tuple[rule_edits.PlannedSourceChange, ...]:
        """Return planned source changes for this fix."""
        return (self._change,)


@dataclasses.dataclass(frozen=True)
class RuleViolation:
    """Canonical issue reported by one rule.

    Attributes:
        finding (RuleFinding): Diagnostic represented by this violation.
        fix (RuleSourceFix | None): Source-edit fix for this violation, if and only if the finding is fixable.
    """

    finding: RuleFinding
    fix: RuleSourceFix | None = None

    def __post_init__(self) -> None:
        """Validate finding and fixability consistency."""
        if not isinstance(self.finding, RuleFinding):
            raise TypeError(f"Rule violation finding must be a RuleFinding, got {type(self.finding).__name__}")
        if self.fix is not None and not isinstance(self.fix, RuleSourceFix):
            raise TypeError(f"Rule violation fix must be a RuleSourceFix, got {type(self.fix).__name__}")
        if (self.fix is not None) != self.finding.fixable:
            raise ValueError("Rule violation fix must be present if and only if the finding is fixable")


def violation_for_planned_source_change(
    rule: RuleMetadata,
    change: rule_edits.PlannedSourceChange,
    *,
    instance_message: str | None = None,
) -> RuleViolation:
    """Return one violation backed by one planned source change."""
    finding = _finding_for_planned_source_change(rule, change, instance_message=instance_message)
    return RuleViolation(finding=finding, fix=RuleSourceFix.from_change(change))


def violation_for_optional_planned_source_change(
    rule: RuleMetadata,
    change: rule_edits.PlannedSourceChange | None,
    *,
    line_numbers: tuple[int, ...] | None = None,
    suppression_line_numbers: tuple[tuple[int, ...], ...] | None = None,
    instance_message: str | None = None,
) -> RuleViolation:
    """Return a change-backed violation when a change exists, otherwise use the explicit diagnostic targets."""
    if change is None:
        if line_numbers is None:
            raise ValueError("Diagnostic-only optional source-change violations must specify line_numbers")
        return diagnostic(rule, line_numbers, suppression_line_numbers=() if suppression_line_numbers is None else suppression_line_numbers, instance_message=instance_message)
    if line_numbers is not None and line_targets.normalize_line_numbers(line_numbers, "Optional source-change violation line numbers") != change.line_numbers:
        raise ValueError("Optional source-change violation line_numbers must match the planned change")
    if (
        suppression_line_numbers is not None
        and line_targets.normalize_line_number_targets(
            suppression_line_numbers, "Optional source-change violation suppression line-number targets", "Optional source-change violation suppression line-number target"
        )
        != change.suppression_line_numbers
    ):
        raise ValueError("Optional source-change violation suppression targets must match the planned change")
    return violation_for_planned_source_change(rule, change, instance_message=instance_message)


def violations_for_planned_source_changes(
    rule: RuleMetadata,
    changes: tuple[rule_edits.PlannedSourceChange, ...],
    *,
    instance_message: str | None = None,
) -> tuple[RuleViolation, ...]:
    """Return one planned-source-backed violation for each source change."""
    return tuple(violation_for_planned_source_change(rule, change, instance_message=instance_message) for change in changes)


def _finding_for_planned_source_change(
    rule: RuleMetadata,
    change: rule_edits.PlannedSourceChange,
    *,
    instance_message: str | None = None,
) -> RuleFinding:
    """Return a finding using one planned change's reported line targets."""
    return RuleFinding(
        rule=rule,
        line_numbers=change.line_numbers,
        suppression_line_numbers=change.suppression_line_numbers,
        instance_message=instance_message,
        instance_fixable=_fixable_instance_fixability(rule),
    )


def diagnostic(rule: RuleMetadata, line_numbers: tuple[int, ...], *, suppression_line_numbers: tuple[tuple[int, ...], ...] = (), instance_message: str | None = None) -> RuleViolation:
    """Return one diagnostic-only violation."""
    return RuleViolation(
        finding=RuleFinding(
            rule=rule, line_numbers=line_numbers, suppression_line_numbers=suppression_line_numbers, instance_message=instance_message, instance_fixable=_diagnostic_instance_fixability(rule)
        ),
        fix=None,
    )


def _diagnostic_instance_fixability(rule: RuleMetadata) -> bool | None:
    """Return instance fixability for a diagnostic-only finding."""
    if rule.fix_availability == FixAvailability.ALWAYS:
        raise ValueError(f"{rule.code}: Always-fixable rules must attach a source fix")
    if rule.fix_availability in {FixAvailability.USUALLY, FixAvailability.SOMETIMES}:
        return False
    return None


def _fixable_instance_fixability(rule: RuleMetadata) -> bool | None:
    """Return instance fixability for a source-fix-backed finding."""
    if rule.fix_availability == FixAvailability.NEVER:
        raise ValueError(f"{rule.code}: Never-fixable rules must not attach a source fix")
    if rule.fix_availability in {FixAvailability.USUALLY, FixAvailability.SOMETIMES}:
        return True
    return None


def _validate_planned_change(change: rule_edits.PlannedSourceChange) -> None:
    """Validate one concrete planned source change."""
    if not isinstance(change, rule_edits.PlannedSourceChange):
        raise TypeError("Rule source fix planned change must be a PlannedSourceChange instance")
