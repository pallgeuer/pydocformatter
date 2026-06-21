from __future__ import annotations

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF002TrailingCommentSpacing(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF002"),
        name="trailing-comment-spacing",
        message="Trailing comment spacing should be normalized",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return trailing comment spacing findings."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply trailing comment spacing fixes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


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
