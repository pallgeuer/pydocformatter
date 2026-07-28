"""PDF100 docstring-indentation rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import dataclasses
from collections.abc import Sequence
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import ascii_whitespace, string_literals, text_layout
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF100DocstringIndentation(RuleBase):
    """Rule implementation for PDF100.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF100"),
        name="docstring-indentation",
        message="Docstring line is incorrectly indented",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for safely normalizable docstring indentation.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe docstring indentation changes."""
    data = PDF_definition.PDF.require_data(context)
    lines = context.source_lines
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: Sequence[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring, require_multiline=True):
        return None
    canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
    line_targets = _target_raw_lines(docstring, canonical_margin=canonical_margin, context=context)
    changed_lines = tuple(
        (line, line_targets[line.index]) for line in docstring.structure.lines if line.index > 0 and line.source_line_number is not None and line.raw_text != line_targets[line.index].raw_text
    )
    if not changed_lines:
        return None
    source_map = docstring.source_map
    if source_map is None:
        return None
    fragments = source_map.fragments
    replacements: list[rule_edits.PlannedTextReplacement] = []
    for line, target in changed_lines:
        line_number = line.source_line_number
        if line_number is not None:
            replacements.append(
                rule_edits.PlannedTextReplacement(
                    start_offset=line.start_offset, end_offset=line.end_offset, text=_source_for_target_line(line, target, context=context, fragments=fragments), line_numbers=(line_number,)
                )
            )

    value_lines = [line_targets[line.index].raw_text if line.index > 0 else line.raw_text for line in docstring.structure.lines]
    return PDF_definition.planned_simple_docstring_source_change(docstring, replacements=tuple(replacements), value_lines=value_lines, source_map=source_map)


@dataclasses.dataclass(frozen=True)
class _LineTarget:
    """Target raw line text and the visual margin stripped from its suffix."""

    raw_text: str
    strip_width: int
    prefix: str


def _target_raw_lines(docstring: PDF_definition.DocstringInfo, *, canonical_margin: str, context: RuleContext) -> tuple[_LineTarget, ...]:
    """Return target evaluated raw text for each docstring line."""
    canonical_margin = _style_normalized_indent(canonical_margin, context=context)
    targets: list[_LineTarget | None] = [None] * len(docstring.structure.lines)
    targets[0] = _LineTarget(docstring.structure.lines[0].raw_text, 0, "")
    for line in docstring.structure.lines[1:]:
        if not text_layout.has_space_tab_content(line.raw_text):
            target = canonical_margin if PDF_definition.is_same_line_closing_delimiter_prefix(docstring, line) else _target_blank_line(line.raw_text, canonical_margin=canonical_margin)
            targets[line.index] = _LineTarget(target, 0, "")

    convention_lines = _apply_convention_targets(targets, docstring, canonical_margin=canonical_margin, context=context)
    plain_indexes = tuple(line.index for line in docstring.structure.lines[1:] if targets[line.index] is None and line.index not in convention_lines and _has_indentation_content(line.raw_text))
    _apply_common_margin_targets(targets, docstring, plain_indexes, canonical_margin)

    for line in docstring.structure.lines[1:]:
        if targets[line.index] is None:
            targets[line.index] = _LineTarget(line.raw_text, 0, "")
        if context.settings.indent_style == settings_check.IndentStyle.SPACE:
            line_target = targets[line.index]
            if line_target is not None:
                targets[line.index] = dataclasses.replace(line_target, raw_text=_space_normalized_target_text(line_target, context=context))
    return tuple(target if target is not None else _LineTarget("", 0, "") for target in targets)


def _target_blank_line(raw_text: str, *, canonical_margin: str) -> str:
    """Return the accepted blank-line indentation state."""
    if raw_text in {"", canonical_margin}:
        return raw_text
    if raw_text.startswith(canonical_margin):
        return canonical_margin
    return ""


def _has_indentation_content(raw_text: str) -> bool:
    """Return whether a line has content safe to include in indentation normalization."""
    content = raw_text.lstrip(ascii_whitespace.SPACE_AND_TAB)
    return bool(content) and not content[:1].isspace()


def _apply_convention_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, *, canonical_margin: str, context: RuleContext) -> set[int]:
    """Apply convention-aware indentation targets and return covered lines."""
    if docstring.structure.convention not in {settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY}:
        return set()
    covered: set[int] = set()
    unit = text_layout.indent_unit(context.settings)
    for section in docstring.structure.sections:
        if section.start_line == 0:
            section_indexes = range(section.start_line, section.end_line)
            _preserve_targets(targets, docstring, section_indexes)
            covered.update(section_indexes)
            continue
        header_end = section.content_start_line
        header_indexes = range(section.start_line, header_end)
        _apply_fixed_prefix_targets(targets, docstring, header_indexes, canonical_margin)
        covered.update(header_indexes)
        entry_indexes: set[int] = set()
        for entry in section.entries:
            prefix = f"{canonical_margin}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else canonical_margin
            _apply_fixed_prefix_targets(targets, docstring, (entry.start_line,), prefix)
            continuation_prefix = f"{canonical_margin}{unit}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else f"{canonical_margin}{unit}"
            _apply_fixed_prefix_targets(targets, docstring, range(entry.start_line + 1, entry.end_line), continuation_prefix)
            entry_indexes.update(range(entry.start_line, entry.end_line))
        covered.update(entry_indexes)
        other_indexes = tuple(index for index in range(header_end, section.end_line) if index not in entry_indexes and _has_indentation_content(docstring.structure.lines[index].raw_text))
        other_prefix = f"{canonical_margin}{unit}" if docstring.structure.convention == settings_check.DocstringConvention.GOOGLE else canonical_margin
        _apply_common_margin_targets(targets, docstring, other_indexes, other_prefix)
        covered.update(other_indexes)
    return covered


def _preserve_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: range) -> None:
    """Assign unchanged targets for structurally non-rewritable lines."""
    for index in indexes:
        line = docstring.structure.lines[index]
        targets[index] = _LineTarget(line.raw_text, 0, "")


def _apply_fixed_prefix_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: range | tuple[int, ...], prefix: str) -> None:
    """Assign targets by replacing each line's full leading whitespace."""
    for index in indexes:
        line = docstring.structure.lines[index]
        if index == 0 or not _has_indentation_content(line.raw_text):
            continue
        targets[index] = _LineTarget(f"{prefix}{line.raw_text[len(line.raw_indent) :]}", text_layout.leading_width(line.raw_indent), prefix)


def _apply_common_margin_targets(targets: list[_LineTarget | None], docstring: PDF_definition.DocstringInfo, indexes: tuple[int, ...], prefix: str) -> None:
    """Assign targets by stripping a shared visual margin before prefixing."""
    if not indexes:
        return
    common_width = min(text_layout.leading_width(docstring.structure.lines[index].raw_text) for index in indexes)
    for index in indexes:
        line = docstring.structure.lines[index]
        targets[index] = _LineTarget(f"{prefix}{text_layout.strip_indent(line.raw_text, common_width)}", common_width, prefix)


def _source_for_target_line(line: PDF_definition.DocstringValueLine, target: _LineTarget, *, context: RuleContext, fragments: tuple[string_literals.StringValueFragment, ...]) -> str:
    """Return source spelling for a target line while preserving suffix spelling."""
    if not text_layout.has_space_tab_content(line.raw_text):
        return target.raw_text
    _, raw_index, virtual_prefix = text_layout.strip_indent_with_mapping(line.raw_text, max(target.strip_width, 0))
    suffix = f"{' ' * virtual_prefix}{''.join(fragment.source for fragment in fragments[line.start_offset + raw_index : line.end_offset])}"
    if context.settings.indent_style == settings_check.IndentStyle.SPACE:
        suffix_content = suffix.lstrip(ascii_whitespace.SPACE_AND_TAB)
        suffix = f"{_style_normalized_indent(suffix, context=context)}{suffix_content}"
    return f"{target.prefix}{suffix}"


def _style_normalized_indent(indent: str, *, context: RuleContext) -> str:
    """Return indentation using the configured style where PDF100 owns generation."""
    if context.settings.indent_style == settings_check.IndentStyle.TAB:
        return indent
    return " " * text_layout.leading_width(indent)


def _space_normalized_target_text(target: _LineTarget, *, context: RuleContext) -> str:
    """Return target text with residual leading tabs expanded after the generated prefix."""
    if target.prefix and target.raw_text.startswith(target.prefix):
        suffix = target.raw_text[len(target.prefix) :]
        suffix_content = suffix.lstrip(ascii_whitespace.SPACE_AND_TAB)
        return f"{target.prefix}{_style_normalized_indent(suffix, context=context)}{suffix_content}"
    content = target.raw_text.lstrip(ascii_whitespace.SPACE_AND_TAB)
    return f"{_style_normalized_indent(target.raw_text, context=context)}{content}"
