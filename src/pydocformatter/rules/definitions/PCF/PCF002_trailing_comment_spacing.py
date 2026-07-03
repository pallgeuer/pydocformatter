"""PCF002 trailing-comment-spacing rule."""

from __future__ import annotations

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF002TrailingCommentSpacing(RuleBase):
    """Rule implementation for PCF002.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF002"),
        name="trailing-comment-spacing",
        message="Trailing comment spacing should be normalized",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return trailing comment spacing violations.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all trailing comment spacing changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    changes: list[rule_edits.PlannedSourceChange] = []
    for comment in data.trailing_comments:
        if comment.kind not in (PCF_definition.CommentKind.REGULAR, PCF_definition.CommentKind.TYPE_DIRECTIVE, PCF_definition.CommentKind.TOOL_DIRECTIVE):
            continue
        code = comment.line_prefix.rstrip(" \t\f")
        if comment.kind == PCF_definition.CommentKind.REGULAR:
            replacement = PCF_definition.render_inline_trailing_comment(code, comment.content)
        else:
            directive_text = comment.text.rstrip(" \t\f")
            replacement = f"{code}  {directive_text}"
        change = PCF_definition.planned_full_line_change(data, comment, replacement)
        if change is not None:
            changes.append(change)
    return tuple(changes)
