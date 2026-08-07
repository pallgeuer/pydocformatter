"""PCF002 trailing-comment-extraction rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import comment_formatting, inline_markup, text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF002TrailingCommentExtraction(RuleBase):
    """Rule implementation for PCF002.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF002"),
        name="trailing-comment-extraction",
        message="Trailing comment should be extracted",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return trailing comment extraction violations.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context)


def _violations(context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return safe extraction fixes and ambiguity-protected findings."""
    data = PCF_definition.PCF.require_data(context)
    comments_by_line = {comment.range.start.line: comment for comment in data.comments}
    violations: list[rule_violations.RuleViolation] = []
    for comment in data.trailing_comments:
        if comment.kind != PCF_definition.CommentKind.REGULAR or not comment.content:
            continue
        code = comment.line_prefix.rstrip(" \t\f")
        inline = comment_formatting.render_inline_trailing_comment(code, comment.content)
        if text_layout.display_width(inline, tab_width=context.settings.indent_width) <= context.settings.line_length:
            continue
        if context.settings.comment_trailing_extraction_syntax_aware and comment.syntax_sensitive:
            continue
        if comment.unicode_occurrences:
            violations.append(rule_violations.diagnostic(PCF002TrailingCommentExtraction.meta, (comment.range.start.line,)))
            continue
        scan = inline_markup.scan_text(comment.content)
        if scan.rewrite_blocked:
            violations.append(rule_violations.diagnostic(PCF002TrailingCommentExtraction.meta, (comment.range.start.line,)))
            continue
        if context.settings.comment_trailing_extraction_content_aware and comment_formatting.trailing_content_is_unsafe(comment.body, settings=context.settings):
            continue
        replacement = _extracted_replacement(comment, code=code, context=context, comments_by_line=comments_by_line, scan=scan)
        change = comment_formatting.planned_full_line_change(data, comment, replacement)
        if change is not None:
            violations.append(rule_violations.violation_for_planned_source_change(PCF002TrailingCommentExtraction.meta, change))
    return tuple(violations)


def _extracted_replacement(
    comment: PCF_definition.CommentInfo, *, code: str, context: RuleContext, comments_by_line: dict[int, PCF_definition.CommentInfo], scan: inline_markup.InlineScanResult
) -> str:
    """Return the full-line replacement for one extracted trailing comment."""
    width = comment_formatting.available_comment_width(comment.indent, line_length=context.settings.line_length, tab_width=context.settings.indent_width)
    task_marker = comment_formatting.task_marker_match(comment.body.strip(), settings=context.settings)
    if task_marker is not None:
        wrapped = comment_formatting.format_task_marker_lines(task_marker.marker, (task_marker.text,), indent=comment.indent, settings=context.settings)
    else:
        wrapped = text_layout.wrap_scanned_text(comment.content, scan, width=width, tab_width=context.settings.indent_width, url_aware=context.settings.url_aware_wrapping)
    comment_lines = tuple(comment_formatting.render_comment(line, indent=comment.indent) for line in wrapped)
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
