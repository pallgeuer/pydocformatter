"""PCF007 comment-suspicious-unicode rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from collections import defaultdict
from typing import TYPE_CHECKING

# Third-party imports
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.definition_helpers import unicode_safety


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF007CommentSuspiciousUnicode(RuleBase):
    """Rule implementation for PCF007.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF007"),
        name="comment-suspicious-unicode",
        message="Comment contains suspicious Unicode",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return suspicious Unicode violations for literal comments.

        Args:
            context (RuleContext): Current file context with parsed module and prepared PCF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Grouped fixable and diagnostic-only findings.
        """
        data = PCF_definition.PCF.require_data(context)
        return tuple(violation for comment in data.comments for violation in _violations_for_comment(comment))


def _violations_for_comment(comment: PCF_definition.CommentInfo) -> tuple[rule_violations.RuleViolation, ...]:
    """Return grouped findings for one comment payload."""
    groups: dict[int, list[unicode_safety.SuspiciousUnicodeOccurrence]] = defaultdict(list)
    for occurrence in comment.unicode_occurrences:
        groups[occurrence.code_point].append(occurrence)
    violations: list[rule_violations.RuleViolation] = []
    for group in groups.values():
        occurrence = group[0]
        changes = tuple(_change(comment, item) for item in group) if all(item.can_fix for item in group) else ()
        message = f"Comment contains suspicious Unicode character {occurrence.code_point_text}"
        violations.append(
            rule_violations.violation_for_grouped_planned_source_changes(PCF007CommentSuspiciousUnicode.meta, changes, instance_message=message)
            if changes
            else rule_violations.diagnostic(PCF007CommentSuspiciousUnicode.meta, (comment.range.start.line,), instance_message=message)
        )
    return tuple(violations)


def _change(comment: PCF_definition.CommentInfo, occurrence: unicode_safety.SuspiciousUnicodeOccurrence) -> rule_edits.PlannedSourceChange:
    """Return one literal comment-character replacement."""
    column = comment.range.start.column + 1 + occurrence.offset
    code_range = cst_metadata.CodeRange(start=cst_metadata.CodePosition(line=comment.range.start.line, column=column), end=cst_metadata.CodePosition(line=comment.range.start.line, column=column + 1))
    return rule_edits.PlannedSourceChange(edit=rule_edits.SourceEdit(range=code_range, replacement=" "), line_numbers=(comment.range.start.line,), suppression_line_numbers=())
