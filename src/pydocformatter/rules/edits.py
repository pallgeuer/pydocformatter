from __future__ import annotations

import dataclasses

import libcst as cst
import libcst.metadata as cst_metadata

from pydocformatter.rules.models import RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class SourceEdit:
    """Replacement of one half-open source range."""

    range: cst_metadata.CodeRange
    replacement: str


@dataclasses.dataclass(frozen=True)
class PlannedSourceChange:
    """One source edit and the lines reported for it."""

    edit: SourceEdit
    line_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class PlannedTextReplacement:
    """Replacement text and the source lines reported for it."""

    start_offset: int
    end_offset: int
    text: str
    line_numbers: tuple[int, ...]


def apply_planned_source_changes(module: cst.Module, changes: tuple[PlannedSourceChange, ...]) -> cst.Module:
    """Apply the source edits from planned changes to a module."""
    return apply_source_edits(module, tuple(change.edit for change in changes))


def findings_for_planned_source_changes(rule: RuleMetadata, changes: tuple[PlannedSourceChange, ...]) -> tuple[RuleFinding, ...]:
    """Return rule findings for planned source changes."""
    return tuple(RuleFinding(rule=rule, line_numbers=change.line_numbers) for change in changes)


def apply_source_edits(module: cst.Module, edits: tuple[SourceEdit, ...]) -> cst.Module:
    """Apply non-overlapping source edits to a module and parse the result."""
    if not edits:
        return module

    source = module.code
    line_bounds = _line_bounds(source)
    indexed_edits = tuple((_range_offsets(edit.range, line_bounds=line_bounds), edit) for edit in edits)
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
        chunks.append(source[cursor:start])
        chunks.append(edit.replacement)
        cursor = end
    chunks.append(source[cursor:])
    return cst.parse_module("".join(chunks), config=module.config_for_parsing)


def _line_bounds(source: str) -> tuple[tuple[int, int], ...]:
    """Return source offsets bounding each line without its line ending."""
    bounds: list[tuple[int, int]] = []
    line_start = 0
    index = 0
    while index < len(source):
        char = source[index]
        if char == "\r":
            bounds.append((line_start, index))
            index += 2 if index + 1 < len(source) and source[index + 1] == "\n" else 1
            line_start = index
        elif char == "\n":
            bounds.append((line_start, index))
            index += 1
            line_start = index
        else:
            index += 1
    bounds.append((line_start, len(source)))
    return tuple(bounds)


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
