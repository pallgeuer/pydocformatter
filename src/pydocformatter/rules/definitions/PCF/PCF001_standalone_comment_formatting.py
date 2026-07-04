"""PCF001 standalone-comment-formatting rule."""

from __future__ import annotations

import re

import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.colon_boundaries as colon_boundaries
import pydocformatter.rules.definition_helpers.comments as comment_helpers
import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import CheckSettings
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF001StandaloneCommentFormatting(RuleBase):
    """Rule implementation for PCF001.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF001"),
        name="standalone-comment-formatting",
        message="Standalone comment needs formatting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return standalone comment formatting violations.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all standalone comment changes for the current source."""
    data = PCF_definition.PCF.require_data(context)
    changes: list[rule_edits.PlannedSourceChange] = []
    for run in data.standalone_runs:
        preserved = comment_helpers.preserved_indices(run, settings=context.settings)
        if comment_helpers.run_contains_code(run, preserved=preserved, settings=context.settings, ignore_task_markers=True):
            continue
        index = 0
        while index < len(run.comments):
            if index in preserved:
                index += 1
                continue
            task_marker_match = comment_helpers.task_marker_match(run.comments[index].body.rstrip()) if context.settings.comment_format_task_markers else None
            list_match = comment_helpers.LIST_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_list_items else None
            quote_match = comment_helpers.BLOCK_QUOTE_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_block_quotes else None
            if task_marker_match is not None:
                end, output_lines = _format_task_marker(run, index, match=task_marker_match, preserved=preserved, settings=context.settings)
            elif list_match is not None:
                end, output_lines = _format_list_item(run, index, match=list_match, preserved=preserved, settings=context.settings)
            elif quote_match is not None:
                end, output_lines = _format_block_quote(run, index, match=quote_match, preserved=preserved, settings=context.settings)
            elif context.settings.comment_join_standalone_lines:
                end = _ordinary_paragraph_end(run, index, preserved=preserved, settings=context.settings)
                content = " ".join(comment.content for comment in run.comments[index:end])
                output_lines = _wrap_plain(content, indent=run.indent, settings=context.settings)
            else:
                end = index + 1
                output_lines = _wrap_plain(run.comments[index].content, indent=run.indent, settings=context.settings)
            change = _change_for_unit(data, run.comments[index:end], output_lines=output_lines, indent=run.indent, line_ending=context.line_ending)
            if change is not None:
                changes.append(change)
            index = end
    return tuple(changes)


def _change_for_unit(
    data: PCF_definition.PCFCategoryData,
    comments: tuple[PCF_definition.CommentInfo, ...],
    *,
    output_lines: tuple[str, ...],
    indent: str,
    line_ending: str,
) -> rule_edits.PlannedSourceChange | None:
    """Build a planned replacement when generated unit source differs."""
    code_range = cst_metadata.CodeRange(start=comments[0].range.start, end=comments[-1].range.end)
    rendered = [PCF_definition.render_comment(output_lines[0], include_indent=False)]
    rendered.extend(PCF_definition.render_comment(line, indent=indent) for line in output_lines[1:])
    replacement = line_ending.join(rendered)
    if data.source_for(code_range) == replacement:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=code_range, replacement=replacement),
        line_numbers=tuple(comment.range.start.line for comment in comments),
        suppression_line_numbers=(),
    )


def _wrap_plain(content: str, *, indent: str, settings: CheckSettings) -> tuple[str, ...]:
    """Wrap ordinary normalized comment content."""
    width = PCF_definition.available_comment_width(indent, line_length=settings.line_length, tab_width=settings.indent_width)
    return text_layout.wrap_text(content, width=width, tab_width=settings.indent_width, url_aware=settings.url_aware_wrapping)


def _format_task_marker(
    run: PCF_definition.StandaloneCommentRun,
    index: int,
    *,
    match: comment_helpers.TaskMarkerMatch,
    preserved: set[int],
    settings: CheckSettings,
) -> tuple[int, tuple[str, ...]]:
    """Return the extent and hanging-indented output of one task marker."""
    texts = [match.text]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        continuation = comment_helpers.task_marker_continuation_text(run.comments[end].body.rstrip(), marker=match.marker)
        if continuation is None:
            break
        texts.append(continuation)
        end += 1
    return end, comment_helpers.format_task_marker_lines(match.marker, tuple(texts), indent=run.indent, settings=settings)


def _format_list_item(
    run: PCF_definition.StandaloneCommentRun,
    index: int,
    *,
    match: re.Match[str],
    preserved: set[int],
    settings: CheckSettings,
) -> tuple[int, tuple[str, ...]]:
    """Return the extent and hanging-indented output of one list item."""
    prefix = _expanded_structure_prefix(f"{match.group('indent')}{match.group('marker')} ", indent=run.indent, tab_width=settings.indent_width)
    texts = [match.group("text").strip()]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        body = run.comments[end].body.rstrip()
        if settings.comment_format_task_markers and comment_helpers.task_marker_match(body) is not None:
            break
        if comment_helpers.LIST_RE.match(body) is not None or comment_helpers.BLOCK_QUOTE_RE.match(body) is not None:
            break
        if not body[:1].isspace():
            break
        texts.append(body.strip())
        end += 1
    width = settings.line_length - text_layout.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    subsequent = " " * len(prefix)
    lines = text_layout.wrap_text(" ".join(texts), width=width, initial_indent=prefix, subsequent_indent=subsequent, tab_width=settings.indent_width, url_aware=settings.url_aware_wrapping)
    return end, lines


def _format_block_quote(
    run: PCF_definition.StandaloneCommentRun,
    index: int,
    *,
    match: re.Match[str],
    preserved: set[int],
    settings: CheckSettings,
) -> tuple[int, tuple[str, ...]]:
    """Return the extent and prefix-preserving output of one block quote."""
    prefix = _expanded_structure_prefix(match.group("prefix"), indent=run.indent, tab_width=settings.indent_width)
    texts = [match.group("text").strip()]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        next_match = comment_helpers.BLOCK_QUOTE_RE.match(run.comments[end].body.rstrip())
        if next_match is None or _expanded_structure_prefix(next_match.group("prefix"), indent=run.indent, tab_width=settings.indent_width) != prefix:
            break
        texts.append(next_match.group("text").strip())
        end += 1
    width = settings.line_length - text_layout.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    lines = text_layout.wrap_text(" ".join(texts), width=width, initial_indent=prefix, subsequent_indent=prefix, tab_width=settings.indent_width, url_aware=settings.url_aware_wrapping)
    return end, lines


def _expanded_structure_prefix(prefix: str, *, indent: str, tab_width: int) -> str:
    """Expand tabs in a generated structure prefix at its source column."""
    base_width = text_layout.display_width(f"{indent}# ", tab_width=tab_width)
    return (" " * base_width + prefix).expandtabs(tab_width)[base_width:]


def _ordinary_paragraph_end(run: PCF_definition.StandaloneCommentRun, index: int, *, preserved: set[int], settings: CheckSettings) -> int:
    """Return the exclusive end of one ordinary prose paragraph."""
    if _is_colon_header(run.comments[index]):
        return index + 1
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        body = run.comments[end].body.rstrip()
        if settings.comment_format_task_markers and comment_helpers.task_marker_match(body) is not None:
            break
        if settings.comment_format_list_items and comment_helpers.LIST_RE.match(body) is not None:
            break
        if settings.comment_format_block_quotes and comment_helpers.BLOCK_QUOTE_RE.match(body) is not None:
            break
        if _is_colon_header(run.comments[end]):
            if _allows_colon_continuation(run.comments[end - 1], run.comments[end]):
                end += 1
            break
        end += 1
    return end


def _is_colon_header(comment: PCF_definition.CommentInfo) -> bool:
    """Return whether a comment line should stop ordinary paragraph joining."""
    return colon_boundaries.is_colon_header_text(comment.content)


def _allows_colon_continuation(previous: PCF_definition.CommentInfo, current: PCF_definition.CommentInfo) -> bool:
    """Return whether a colon-ended comment may continue the previous prose line."""
    return colon_boundaries.allows_colon_continuation(previous.content, current.content)
