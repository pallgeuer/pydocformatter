from __future__ import annotations

import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF002TrailingCommentFormatting(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF002"),
        name="trailing-comment-formatting",
        message="Trailing comment needs formatting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return trailing comment formatting findings."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply trailing comment formatting fixes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all trailing comment changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    changes: list[rule_edits.PlannedSourceChange] = []
    for comment in data.trailing_comments:
        if comment.kind != PCF_definition.CommentKind.REGULAR:
            continue
        code = comment.line_prefix.rstrip(" \t\f")
        content = comment.content
        inline = f"{code}  # {content}" if content else f"{code}  #"
        if not content or text_layout.display_width(inline, tab_width=context.settings.indent_width) <= context.settings.line_length:
            replacement = inline
        else:
            width = PCF_definition.available_comment_width(
                comment.indent,
                line_length=context.settings.line_length,
                tab_width=context.settings.indent_width,
            )
            wrapped = text_layout.wrap_text(content, width=width)
            comment_lines = tuple(PCF_definition.render_comment(line, indent=comment.indent) for line in wrapped)
            if _requires_standalone_boundary(data, comment):
                comment_lines = ("", *comment_lines)
            replacement = context.line_ending.join((*comment_lines, code))
        code_range = cst_metadata.CodeRange(
            start=cst_metadata.CodePosition(line=comment.range.start.line, column=0),
            end=comment.range.end,
        )
        if data.source_for(code_range) == replacement:
            continue
        changes.append(
            rule_edits.PlannedSourceChange(
                edit=rule_edits.SourceEdit(range=code_range, replacement=replacement),
                line_numbers=(comment.range.start.line,),
            )
        )
    return tuple(changes)


def _requires_standalone_boundary(data: PCF_definition.PCFCategoryData, comment: PCF_definition.CommentInfo) -> bool:
    """Return whether extraction would join a preceding standalone comment run."""
    for previous in reversed(data.comments):
        if previous.range.start.line >= comment.range.start.line:
            continue
        if previous.range.start.line < comment.range.start.line - 1:
            return False
        return (
            previous.placement == PCF_definition.CommentPlacement.STANDALONE
            and previous.kind == PCF_definition.CommentKind.REGULAR
            and not previous.is_empty
            and not previous.is_hash_only
            and previous.indent == comment.indent
        )
    return False
