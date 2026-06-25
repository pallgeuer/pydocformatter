"""Source edit planning and application for rules."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import libcst as cst
import libcst.metadata as cst_metadata

import pydocformatter.rules.definition_helpers.source_text as source_text
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata

if TYPE_CHECKING:
    from pydocformatter.rules.definition import RuleCategoryContext


@dataclasses.dataclass(frozen=True)
class SourceEdit:
    """Replacement of one half-open source range.

    Attributes:
        range (cst_metadata.CodeRange): Half-open source range to replace.
        replacement (str): Source text inserted in place of `range`.
    """

    range: cst_metadata.CodeRange
    replacement: str


@dataclasses.dataclass(frozen=True)
class PlannedSourceChange:
    """One source edit and the lines reported for it.

    Attributes:
        edit (SourceEdit): Concrete source edit to apply.
        line_numbers (tuple[int, ...]): One-based source lines reported for the associated finding.
    """

    edit: SourceEdit
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class PlannedTextReplacement:
    """Replacement text and the source lines reported for it.

    Attributes:
        start_offset (int): Start offset in the original source text.
        end_offset (int): End offset in the original source text.
        text (str): Replacement source text.
        line_numbers (tuple[int, ...]): One-based source lines reported for the associated finding.
    """

    start_offset: int
    end_offset: int
    text: str
    line_numbers: tuple[int, ...]


def apply_planned_source_changes(
    module: cst.Module,
    changes: tuple[PlannedSourceChange, ...],
    *,
    source: str | None = None,
    line_bounds: source_text.LineBounds | None = None,
) -> cst.Module:
    """Apply the source edits from planned changes to a module."""
    return apply_source_edits(module, tuple(change.edit for change in changes), source=source, line_bounds=line_bounds)


def apply_context_source_changes(context: RuleCategoryContext, changes: tuple[PlannedSourceChange, ...]) -> cst.Module:
    """Apply planned source changes using cached context source data when available."""
    edits = tuple(change.edit for change in changes)
    if context.line_bounds is None:
        return apply_source_edits(context.module, edits)
    return apply_source_edits(context.module, edits, source=context.source, line_bounds=context.line_bounds)


def findings_for_planned_source_changes(rule: RuleMetadata, changes: tuple[PlannedSourceChange, ...], *, instance_fixable: bool | None = None) -> tuple[RuleFinding, ...]:
    """Return rule findings for planned source changes."""
    if rule.fix_availability in {FixAvailability.USUALLY, FixAvailability.SOMETIMES} and instance_fixable is None:
        raise ValueError(f"{rule.code}: Findings for {rule.fix_availability.lower()}-fixable rules must specify instance_fixable")
    return tuple(RuleFinding(rule=rule, line_numbers=change.line_numbers, instance_fixable=instance_fixable) for change in changes)


def apply_source_edits(
    module: cst.Module,
    edits: tuple[SourceEdit, ...],
    *,
    source: str | None = None,
    line_bounds: source_text.LineBounds | None = None,
) -> cst.Module:
    """Apply non-overlapping source edits to a module and parse the result."""
    if (source is None) != (line_bounds is None):
        raise ValueError("source and line_bounds must be provided together")
    if not edits:
        return module

    edit_source = module.code if source is None else source
    edit_line_bounds = source_text.line_bounds_from_lines(source_text.source_lines(edit_source)) if line_bounds is None else line_bounds
    indexed_edits = tuple((_range_offsets(edit.range, line_bounds=edit_line_bounds), edit) for edit in edits)
    sorted_edits = tuple(sorted(indexed_edits, key=lambda item: item[0]))

    previous_start = -1
    previous_end = -1
    for (start, end), edit in sorted_edits:
        if start > end:
            raise ValueError(f"Source edit range starts after it ends: {edit.range}")
        if start < previous_end or start == previous_start:
            raise ValueError(f"Source edits must not overlap: {edit.range}")
        previous_start = start
        previous_end = end

    chunks: list[str] = []
    cursor = 0
    for (start, end), edit in sorted_edits:
        chunks.append(edit_source[cursor:start])
        chunks.append(edit.replacement)
        cursor = end
    chunks.append(edit_source[cursor:])
    return cst.parse_module("".join(chunks), config=module.config_for_parsing)


def _range_offsets(code_range: cst_metadata.CodeRange, *, line_bounds: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    """Convert a LibCST code range to source string offsets."""
    start = _position_offset(code_range.start, line_bounds=line_bounds)
    end = _position_offset(code_range.end, line_bounds=line_bounds)
    return start, end


def _position_offset(position: cst_metadata.CodePosition, *, line_bounds: tuple[tuple[int, int], ...]) -> int:
    """Convert a one-based LibCST line and zero-based column to a string offset."""
    if position.line < 1 or position.line > len(line_bounds):
        raise ValueError(f"Source position line is outside the source: {position}")
    line_start, line_end = line_bounds[position.line - 1]
    if position.column < 0 or line_start + position.column > line_end:
        raise ValueError(f"Source position column is outside the source line: {position}")
    return line_start + position.column
