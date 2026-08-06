"""Source edit planning and application for rules."""

# Future imports
from __future__ import annotations

# Standard library imports
import operator
import dataclasses
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst
import libcst.metadata as cst_metadata

# First-party imports
from pydocformatter.rules import line_targets
from pydocformatter.rules.definition_helpers import source_text


if TYPE_CHECKING:
    # First-party imports
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
        suppression_line_numbers (tuple[tuple[int, ...], ...]): Additional line-number targets used only for source
            suppression matching.
    """

    edit: SourceEdit
    line_numbers: tuple[int, ...]
    suppression_line_numbers: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        """Validate planned change target lines."""
        object.__setattr__(self, "line_numbers", line_targets.normalize_line_numbers(self.line_numbers, "Planned source change line numbers"))
        object.__setattr__(
            self,
            "suppression_line_numbers",
            line_targets.normalize_line_number_targets(self.suppression_line_numbers, "Planned source change suppression line-number targets", "Planned source change suppression line-number target"),
        )


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


@dataclasses.dataclass(frozen=True)
class AppliedSourceChanges:
    """Reparsed module and exact edited source.

    Attributes:
        module (cst.Module): Module reparsed from the edited source.
        source (str): Exact edited source before LibCST rendering normalization.
    """

    module: cst.Module
    source: str


def apply_context_source_changes(context: RuleCategoryContext, changes: tuple[PlannedSourceChange, ...]) -> AppliedSourceChanges:
    """Apply planned source changes using cached context source data when available.

    Args:
        context (RuleCategoryContext): Current module context, including original source and line bounds when available.
        changes (tuple[PlannedSourceChange, ...]): Planned source-level changes to apply in order-independent form.

    Returns:
        AppliedSourceChanges: Reparsed module and exact source after applying the planned changes.
    """
    edits = tuple(change.edit for change in changes)
    line_bounds = source_text.line_bounds_from_lines(context.source_lines) if context.line_bounds is None else context.line_bounds
    return apply_source_edits(context.module, edits, source=context.source, line_bounds=line_bounds)


def apply_source_edits(module: cst.Module, edits: tuple[SourceEdit, ...], *, source: str | None = None, line_bounds: source_text.LineBounds | None = None) -> AppliedSourceChanges:
    """Apply non-overlapping source edits to a module and parse the result.

    Args:
        module (cst.Module): Original parsed module to return unchanged when there are no edits.
        edits (tuple[SourceEdit, ...]): Source replacements with LibCST ranges that must not overlap.
        source (str | None): Original source text to edit, required when precomputed line bounds are supplied.
        line_bounds (source_text.LineBounds | None): Absolute offsets for each physical source line.

    Returns:
        AppliedSourceChanges: Reparsed module and exact source after applying all source edits.

    Raises:
        ValueError: If only one of `source` and `line_bounds` is supplied or if edit ranges overlap.
    """
    if (source is None) != (line_bounds is None):
        raise ValueError("source and line_bounds must be provided together")
    if not edits:
        return AppliedSourceChanges(module=module, source=module.code if source is None else source)

    edit_source = module.code if source is None else source
    edit_line_bounds = source_text.line_bounds_from_lines(source_text.source_lines(edit_source)) if line_bounds is None else line_bounds
    indexed_edits = tuple((_range_offsets(edit.range, line_bounds=edit_line_bounds), edit) for edit in edits)
    sorted_edits = tuple(sorted(indexed_edits, key=operator.itemgetter(0)))

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
        chunks.extend((edit_source[cursor:start], edit.replacement))
        cursor = end
    chunks.append(edit_source[cursor:])
    edited_source = "".join(chunks)
    return AppliedSourceChanges(module=cst.parse_module(edited_source, config=module.config_for_parsing), source=edited_source)


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
