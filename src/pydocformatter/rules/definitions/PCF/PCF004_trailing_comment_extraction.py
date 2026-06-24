from __future__ import annotations

import pydocformatter.rules.definition_helpers.comments as comment_helpers
import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF004TrailingCommentExtraction(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF004"),
        name="trailing-comment-extraction",
        message="Trailing comment should be extracted",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return trailing comment extraction findings."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Apply trailing comment extraction fixes."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all trailing comment extraction changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    comments_by_line = {comment.range.start.line: comment for comment in data.comments}
    changes: list[rule_edits.PlannedSourceChange] = []
    for comment in data.trailing_comments:
        if comment.kind != PCF_definition.CommentKind.REGULAR or not comment.content:
            continue
        code = comment.line_prefix.rstrip(" \t\f")
        inline = PCF_definition.render_inline_trailing_comment(code, comment.content)
        if text_layout.display_width(inline, tab_width=context.settings.indent_width) <= context.settings.line_length:
            continue
        if context.settings.comment_trailing_extraction_syntax_aware and comment.syntax_sensitive:
            continue
        if context.settings.comment_trailing_extraction_content_aware and comment_helpers.trailing_content_is_unsafe(comment.body, settings=context.settings):
            continue
        replacement = _extracted_replacement(data, comment, code=code, context=context, comments_by_line=comments_by_line)
        change = PCF_definition.planned_full_line_change(data, comment, replacement)
        if change is not None:
            changes.append(change)
    return tuple(changes)


def _extracted_replacement(
    data: PCF_definition.PCFCategoryData,
    comment: PCF_definition.CommentInfo,
    *,
    code: str,
    context: RuleContext,
    comments_by_line: dict[int, PCF_definition.CommentInfo],
) -> str:
    """Return the full-line replacement for one extracted trailing comment."""
    width = PCF_definition.available_comment_width(
        comment.indent,
        line_length=context.settings.line_length,
        tab_width=context.settings.indent_width,
    )
    wrapped = text_layout.wrap_text(comment.content, width=width, tab_width=context.settings.indent_width, url_aware=context.settings.url_aware_wrapping)
    comment_lines = tuple(PCF_definition.render_comment(line, indent=comment.indent) for line in wrapped)
    if _requires_standalone_boundary(comment, comments_by_line=comments_by_line):
        comment_lines = ("", *comment_lines)
    return context.line_ending.join((*comment_lines, code))


def _requires_standalone_boundary(comment: PCF_definition.CommentInfo, *, comments_by_line: dict[int, PCF_definition.CommentInfo]) -> bool:
    """Return whether extraction would join a preceding standalone comment run."""
    previous = comments_by_line.get(comment.range.start.line - 1)
    return (
        previous is not None
        and previous.placement == PCF_definition.CommentPlacement.STANDALONE
        and previous.kind == PCF_definition.CommentKind.REGULAR
        and not previous.is_empty
        and not previous.is_hash_only
        and previous.indent == comment.indent
    )
