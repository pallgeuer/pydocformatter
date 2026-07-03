"""Terminal punctuation violation helpers."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable

import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.models import RuleMetadata


@dataclasses.dataclass(frozen=True)
class TerminalPunctuationPolicy:
    """Policy for one terminal-punctuation rule.

    Attributes:
        valid_endings: Terminal characters accepted by the rule.
        nonfixable_endings: Terminal characters that should report but not be rewritten automatically.
    """

    valid_endings: str
    nonfixable_endings: str


def violation(
    *,
    text: str,
    policy: TerminalPunctuationPolicy,
    rule: RuleMetadata,
    line_numbers: tuple[int, ...],
    planned_change: Callable[[], rule_edits.PlannedSourceChange | None],
) -> rule_violations.RuleViolation | None:
    """Return one terminal-punctuation violation.

    Args:
        text: Target text whose terminal punctuation should be checked.
        policy: Valid and non-fixable terminal punctuation policy.
        rule: Rule metadata used for diagnostics and fixes.
        line_numbers: Source line numbers reported for the target text.
        planned_change: Callback that plans the automatic fix only when needed.

    Returns:
        Terminal-punctuation violation, or None when the target text already complies.
    """
    trimmed = text.rstrip(" \t")
    if not trimmed or trimmed.endswith("\\") or trimmed.endswith(tuple(policy.valid_endings)):
        return None
    change = None if trimmed.endswith(tuple(policy.nonfixable_endings)) else planned_change()
    return rule_violations.violation_for_optional_planned_source_change(rule, change, line_numbers=line_numbers)
