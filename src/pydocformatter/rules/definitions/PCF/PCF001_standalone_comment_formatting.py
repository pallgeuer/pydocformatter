"""PCF001 standalone-comment-formatting rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst.metadata as cst_metadata

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.definition_helpers.comments as comment_helpers
from pydocformatter.cli.settings_check import CommentTaskMarkerMode
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import colon_boundaries, inline_markup, text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # Standard library imports
    import re

    # First-party imports
    from pydocformatter.cli.settings_check import CheckSettings
    from pydocformatter.rules.definition import RuleContext


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
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return standalone comment formatting violations.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _violations(context)


@dataclasses.dataclass(frozen=True)
class _SemanticLine:
    """One comment payload line before whitespace normalization.

    Attributes:
        text (str): Semantic text including any terminal hard-break suffix.
        has_following_newline (bool): Whether the physical source line ends with a newline.
    """

    text: str
    has_following_newline: bool


@dataclasses.dataclass(frozen=True)
class _FormattedUnit:
    """Canonical output and safety state for one formatter unit.

    Attributes:
        end (int): Exclusive comment index where the unit ends.
        output_lines (tuple[str, ...]): Canonical comment payload lines.
        ambiguous (bool): Whether conservative markup evidence prohibits the canonical rewrite.
    """

    end: int
    output_lines: tuple[str, ...]
    ambiguous: bool


def _violations(context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
    """Return safe fixes and ambiguity-protected standalone findings."""
    data = PCF_definition.PCF.require_data(context)
    violations: list[rule_violations.RuleViolation] = []
    for run in data.standalone_runs:
        preserved = comment_helpers.preserved_indices(run, settings=context.settings)
        if comment_helpers.run_contains_code(run, preserved=preserved, settings=context.settings, ignore_task_markers=True):
            continue
        index = 0
        while index < len(run.comments):
            if index in preserved:
                index += 1
                continue
            task_marker_match = comment_helpers.task_marker_match(run.comments[index].body.rstrip(), settings=context.settings)
            list_match = comment_helpers.LIST_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_list_items else None
            quote_match = comment_helpers.BLOCK_QUOTE_RE.match(run.comments[index].body.rstrip()) if context.settings.comment_format_block_quotes else None
            if task_marker_match is not None:
                formatted = _format_task_marker(data, run, index, match=task_marker_match, preserved=preserved, settings=context.settings)
            elif list_match is not None:
                formatted = _format_list_item(data, run, index, match=list_match, preserved=preserved, settings=context.settings)
            elif quote_match is not None:
                formatted = _format_block_quote(data, run, index, match=quote_match, preserved=preserved, settings=context.settings)
            elif context.settings.comment_join_standalone_lines:
                end = _ordinary_paragraph_end(run, index, preserved=preserved, settings=context.settings)
                formatted = dataclasses.replace(_format_plain(data, run.comments[index:end], indent=run.indent, settings=context.settings), end=end)
            else:
                end = index + 1
                formatted = dataclasses.replace(_format_plain(data, run.comments[index:end], indent=run.indent, settings=context.settings), end=end)
            comments = run.comments[index : formatted.end]
            canonical_change = _change_for_unit(data, comments, output_lines=formatted.output_lines, indent=run.indent, line_ending=context.line_ending)
            if canonical_change is not None:
                if formatted.ambiguous:
                    marker_change = _marker_only_change(data, comments)
                    violations.append(
                        rule_violations.violation_for_optional_planned_source_change(
                            PCF001StandaloneCommentFormatting.meta, marker_change, line_numbers=tuple(comment.range.start.line for comment in comments)
                        )
                    )
                else:
                    violations.append(rule_violations.violation_for_planned_source_change(PCF001StandaloneCommentFormatting.meta, canonical_change))
            index = formatted.end
    return tuple(violations)


def _change_for_unit(
    data: PCF_definition.PCFCategoryData, comments: tuple[PCF_definition.CommentInfo, ...], *, output_lines: tuple[str, ...], indent: str, line_ending: str
) -> rule_edits.PlannedSourceChange | None:
    """Build a planned replacement when generated unit source differs."""
    code_range = cst_metadata.CodeRange(start=comments[0].range.start, end=comments[-1].range.end)
    rendered = [PCF_definition.render_comment(output_lines[0], include_indent=False)]
    rendered.extend(PCF_definition.render_comment(line, indent=indent) for line in output_lines[1:])
    replacement = line_ending.join(rendered)
    if data.source_for(code_range) == replacement:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=code_range, replacement=replacement), line_numbers=tuple(comment.range.start.line for comment in comments), suppression_line_numbers=()
    )


def _format_plain(data: PCF_definition.PCFCategoryData, comments: tuple[PCF_definition.CommentInfo, ...], *, indent: str, settings: CheckSettings) -> _FormattedUnit:
    """Return canonical output for ordinary comment payload lines."""
    width = PCF_definition.available_comment_width(indent, line_length=settings.line_length, tab_width=settings.indent_width)
    lines = tuple(_SemanticLine(text=comment.body.lstrip(), has_following_newline=_has_following_newline(data, comment)) for comment in comments)
    output, ambiguous = _format_semantic_lines(lines, width=width, initial_prefix="", subsequent_prefix="", settings=settings)
    return _FormattedUnit(end=0, output_lines=output, ambiguous=ambiguous)


def _format_task_marker(
    data: PCF_definition.PCFCategoryData, run: PCF_definition.StandaloneCommentRun, index: int, *, match: comment_helpers.TaskMarkerMatch, preserved: set[int], settings: CheckSettings
) -> _FormattedUnit:
    """Return the extent and hanging-indented output of one task marker."""
    first_body = run.comments[index].body
    first_prefix = f"{match.marker}:"
    texts = [_SemanticLine(text=first_body[len(first_prefix) :].lstrip(" \t"), has_following_newline=_has_following_newline(data, run.comments[index]))]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        continuation = comment_helpers.task_marker_continuation_text(run.comments[end].body.rstrip(), marker=match.marker)
        if continuation is None:
            break
        continuation_prefix = " " * len(f"{match.marker}: ")
        texts.append(_SemanticLine(text=run.comments[end].body[len(continuation_prefix) :], has_following_newline=_has_following_newline(data, run.comments[end])))
        end += 1
    normalized_texts = tuple(line.text.rstrip() for line in texts)
    if settings.comment_task_marker_mode == CommentTaskMarkerMode.NO_WRAP or comment_helpers.task_marker_texts_are_code_like(normalized_texts, settings=settings):
        output, ambiguous = _format_unwrapped_semantic_lines(texts, initial_prefix=f"{match.marker}: ", subsequent_prefix=" " * len(f"{match.marker}: "))
    else:
        width = PCF_definition.available_comment_width(run.indent, line_length=settings.line_length, tab_width=settings.indent_width)
        output, ambiguous = _format_semantic_lines(tuple(texts), width=width, initial_prefix=f"{match.marker}: ", subsequent_prefix=" " * len(f"{match.marker}: "), settings=settings)
    return _FormattedUnit(end=end, output_lines=output, ambiguous=ambiguous)


def _format_list_item(
    data: PCF_definition.PCFCategoryData, run: PCF_definition.StandaloneCommentRun, index: int, *, match: re.Match[str], preserved: set[int], settings: CheckSettings
) -> _FormattedUnit:
    """Return the extent and hanging-indented output of one list item."""
    prefix = _expanded_structure_prefix(f"{match.group('indent')}{match.group('marker')} ", indent=run.indent, tab_width=settings.indent_width)
    texts = [_SemanticLine(text=run.comments[index].body[match.start("text") :], has_following_newline=_has_following_newline(data, run.comments[index]))]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        body = run.comments[end].body.rstrip()
        if comment_helpers.task_marker_match(body, settings=settings) is not None:
            break
        if comment_helpers.LIST_RE.match(body) is not None or comment_helpers.BLOCK_QUOTE_RE.match(body) is not None:
            break
        if not body[:1].isspace():
            break
        texts.append(_SemanticLine(text=run.comments[end].body.lstrip(), has_following_newline=_has_following_newline(data, run.comments[end])))
        end += 1
    width = settings.line_length - text_layout.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    subsequent = " " * len(prefix)
    lines, ambiguous = _format_semantic_lines(tuple(texts), width=width, initial_prefix=prefix, subsequent_prefix=subsequent, settings=settings)
    return _FormattedUnit(end=end, output_lines=lines, ambiguous=ambiguous)


def _format_block_quote(
    data: PCF_definition.PCFCategoryData, run: PCF_definition.StandaloneCommentRun, index: int, *, match: re.Match[str], preserved: set[int], settings: CheckSettings
) -> _FormattedUnit:
    """Return the extent and prefix-preserving output of one block quote."""
    prefix = _expanded_structure_prefix(match.group("prefix"), indent=run.indent, tab_width=settings.indent_width)
    texts = [_SemanticLine(text=run.comments[index].body[match.start("text") :], has_following_newline=_has_following_newline(data, run.comments[index]))]
    end = index + 1
    while end < len(run.comments) and end not in preserved:
        next_match = comment_helpers.BLOCK_QUOTE_RE.match(run.comments[end].body.rstrip())
        if next_match is None or _expanded_structure_prefix(next_match.group("prefix"), indent=run.indent, tab_width=settings.indent_width) != prefix:
            break
        texts.append(_SemanticLine(text=run.comments[end].body[next_match.start("text") :], has_following_newline=_has_following_newline(data, run.comments[end])))
        end += 1
    width = settings.line_length - text_layout.display_width(f"{run.indent}# ", tab_width=settings.indent_width)
    lines, ambiguous = _format_semantic_lines(tuple(texts), width=width, initial_prefix=prefix, subsequent_prefix=prefix, settings=settings)
    return _FormattedUnit(end=end, output_lines=lines, ambiguous=ambiguous)


def _format_semantic_lines(lines: tuple[_SemanticLine, ...], *, width: int, initial_prefix: str, subsequent_prefix: str, settings: CheckSettings) -> tuple[tuple[str, ...], bool]:
    """Wrap semantic lines without joining across explicit hard breaks."""
    layout = inline_markup.scan_layout_lines(tuple(inline_markup.layout_line_for_text(line.text, has_following_newline=line.has_following_newline) for line in lines))
    output: list[str] = []
    for index, segment in enumerate(layout.segments):
        segment_prefix = initial_prefix if index == 0 else subsequent_prefix
        suffix_width = 0 if segment.hard_break is None else text_layout.display_width(segment.hard_break.source, tab_width=settings.indent_width)
        if suffix_width:
            wrapped = text_layout.wrap_inline_tokens(
                segment.scan.tokens,
                width=width,
                initial_indent=segment_prefix,
                subsequent_indent=subsequent_prefix,
                tab_width=settings.indent_width,
                final_suffix_width=suffix_width,
                url_aware=settings.url_aware_wrapping,
            )
        else:
            wrapped = text_layout.wrap_scanned_text(
                segment.text, segment.scan, width=width, initial_indent=segment_prefix, subsequent_indent=subsequent_prefix, tab_width=settings.indent_width, url_aware=settings.url_aware_wrapping
            )
        if segment.hard_break is not None:
            wrapped = (*wrapped[:-1], f"{wrapped[-1]}{segment.hard_break.value}")
        output.extend(wrapped)
    return tuple(output), layout.ambiguous


def _format_unwrapped_semantic_lines(lines: list[_SemanticLine], *, initial_prefix: str, subsequent_prefix: str) -> tuple[tuple[str, ...], bool]:
    """Normalize task-marker lines without prose wrapping or line joining."""
    output: list[str] = []
    ambiguous = False
    for index, line in enumerate(lines):
        layout = inline_markup.scan_layout_lines((inline_markup.layout_line_for_text(line.text, has_following_newline=line.has_following_newline),))
        segment = layout.segments[0]
        ambiguous = ambiguous or layout.ambiguous
        prefix = initial_prefix if index == 0 else subsequent_prefix
        normalized = " ".join(token.value for token in segment.scan.tokens)
        rendered = prefix.rstrip() if not normalized else f"{prefix}{normalized}"
        if segment.hard_break is not None:
            rendered = f"{rendered}{segment.hard_break.value}"
        output.append(rendered)
    return tuple(output), ambiguous


def _marker_only_change(data: PCF_definition.PCFCategoryData, comments: tuple[PCF_definition.CommentInfo, ...]) -> rule_edits.PlannedSourceChange | None:
    """Return a spacing-only edit that preserves comment bodies and line endings."""
    rendered: list[str] = []
    changed = False
    for index, comment in enumerate(comments):
        if index > 0:
            gap = cst_metadata.CodeRange(start=comments[index - 1].range.end, end=comment.range.start)
            rendered.append(data.source_for(gap))
        raw_content = comment.raw_content
        if raw_content and not raw_content.startswith(" ") and comment.content:
            rendered.append(f"# {raw_content}")
            changed = True
        else:
            rendered.append(comment.text)
    if not changed:
        return None
    code_range = cst_metadata.CodeRange(start=comments[0].range.start, end=comments[-1].range.end)
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=code_range, replacement="".join(rendered)), line_numbers=tuple(comment.range.start.line for comment in comments), suppression_line_numbers=()
    )


def _has_following_newline(data: PCF_definition.PCFCategoryData, comment: PCF_definition.CommentInfo) -> bool:
    """Return whether a comment's physical source line has a newline."""
    return data.source_lines[comment.range.start.line - 1].endswith(("\r", "\n"))


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
        if comment_helpers.task_marker_match(body, settings=settings) is not None:
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
