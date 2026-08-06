"""PDF200 too-many-blank-lines rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third-party imports
import libcst as cst

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_rendering, docstring_sections, docstring_source
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.edits as rule_edits
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF200TooManyBlankLines(RuleBase):
    """Rule implementation for PDF200.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF200"),
        name="too-many-blank-lines",
        message="Docstring has too many blank lines",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for excess blank lines in docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe blank-line collapse changes."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not docstring_source.can_canonically_rewrite_simple_docstring(docstring):
        return None
    # Narrow for typing after the safe-mapping predicate.
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    retained_lines = _retained_line_indexes(docstring.structure.blocks, convention=docstring.structure.convention)
    output_lines: tuple[docstring_rendering.DocstringOutputLine, ...]
    if retained_lines is None:
        retained_lines = ()
        output_lines = ()
    else:
        retained_lines = _with_opening_quote_suffix_line(docstring, retained_lines)
        retained_lines = _with_configured_final_section_blank(docstring, retained_lines, context=context)
        retained_lines = _with_closing_quote_prefix_line(docstring, retained_lines)
        output_lines = _output_lines(docstring, retained_lines)
    retained_line_set = set(retained_lines)
    changed_line_numbers = tuple(line.source_line_number for line in docstring.structure.lines if line.index not in retained_line_set and line.source_line_number is not None)
    if not changed_line_numbers:
        return None
    return docstring_rendering.planned_simple_docstring_output_change(
        docstring,
        context=context,
        output_lines=output_lines,
        line_numbers=changed_line_numbers,
        preserve_trailing_newline=bool(retained_lines) and docstring_source.docstring_value_ends_with_newline(docstring),
    )


def _retained_line_indexes(
    blocks: tuple[PDF_definition.DocstringBlock, ...], *, convention: settings_check.DocstringConvention, parent_kind: PDF_definition.DocstringBlockKind | None = None
) -> tuple[int, ...] | None:
    """Return retained logical lines, or None if a blank-only range becomes empty."""
    if not blocks:
        return ()
    non_blank_indexes = tuple(index for index, block in enumerate(blocks) if block.kind is not PDF_definition.DocstringBlockKind.BLANK)
    if not non_blank_indexes:
        return None

    retained: list[int] = []
    first_chunk = non_blank_indexes[0]
    last_chunk = non_blank_indexes[-1]
    previous_block: PDF_definition.DocstringBlock | None = None
    for index, block in enumerate(blocks[first_chunk : last_chunk + 1], start=first_chunk):
        if block.kind is PDF_definition.DocstringBlockKind.BLANK:
            next_block = _next_non_blank_block(blocks, index + 1, last_chunk + 1)
            if not _should_drop_blank_separator(parent_kind, previous_block, next_block, convention=convention):
                retained.append(block.start_line)
            continue
        previous_block = block
        child_lines = _retained_line_indexes(block.children, convention=convention, parent_kind=block.kind)
        if child_lines is None:
            child_lines = ()
        if child_lines:
            retained.extend(child_lines)
        else:
            retained.extend(range(block.start_line, block.end_line))
        if (
            parent_kind is None
            and _keeps_blank_separator_after_section(block, _next_non_blank_block(blocks, index + 1, last_chunk + 1), convention=convention)
            and (trailing_blank_line := _trailing_blank_line(block)) is not None
        ):
            retained.append(trailing_blank_line)
    return tuple(retained)


def _next_non_blank_block(blocks: tuple[PDF_definition.DocstringBlock, ...], start: int, end: int) -> PDF_definition.DocstringBlock | None:
    """Return the next non-blank sibling block in a bounded range."""
    for block in blocks[start:end]:
        if block.kind is not PDF_definition.DocstringBlockKind.BLANK:
            return block
    return None


def _should_drop_blank_separator(
    parent_kind: PDF_definition.DocstringBlockKind | None,
    previous_block: PDF_definition.DocstringBlock | None,
    next_block: PDF_definition.DocstringBlock | None,
    *,
    convention: settings_check.DocstringConvention,
) -> bool:
    """Return whether convention section spacing requires no blank separator."""
    if previous_block is None or next_block is None:
        return False
    if parent_kind is PDF_definition.DocstringBlockKind.SECTION:
        if previous_block.kind is PDF_definition.DocstringBlockKind.SECTION_HEADER:
            return True
        return previous_block.kind is PDF_definition.DocstringBlockKind.SECTION_ENTRY and next_block.kind is PDF_definition.DocstringBlockKind.SECTION_ENTRY
    if convention is settings_check.DocstringConvention.REST:
        return previous_block.kind is PDF_definition.DocstringBlockKind.REST_FIELD and next_block.kind is PDF_definition.DocstringBlockKind.REST_FIELD
    return False


def _keeps_blank_separator_after_section(block: PDF_definition.DocstringBlock, next_block: PDF_definition.DocstringBlock | None, *, convention: settings_check.DocstringConvention) -> bool:
    """Return whether a section trailing blank separates it from another section."""
    return (
        convention in {settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY}
        and block.kind is PDF_definition.DocstringBlockKind.SECTION
        and next_block is not None
        and next_block.kind is PDF_definition.DocstringBlockKind.SECTION
        and _trailing_blank_line(block) is not None
    )


def _trailing_blank_line(block: PDF_definition.DocstringBlock) -> int | None:
    """Return the first trailing blank line in a block."""
    trailing_blank = block.children[-1] if block.children and block.children[-1].kind is PDF_definition.DocstringBlockKind.BLANK else None
    return None if trailing_blank is None else trailing_blank.start_line


def _output_lines(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> tuple[docstring_rendering.DocstringOutputLine, ...]:
    """Return replacement logical lines for retained docstring indexes."""
    return tuple(
        docstring_rendering.DocstringOutputLine(original=line, strip_docstring_margin=output_index == 0 and line.index != 0, source=None, value=None)
        for output_index, line_index in enumerate(retained_lines)
        for line in (docstring.structure.lines[line_index],)
    )


def _with_configured_final_section_blank(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...], *, context: RuleContext) -> tuple[int, ...]:
    """Preserve one trailing blank after the final convention section when configured."""
    if not context.settings.docstring_blank_line_after_last_section:
        return retained_lines
    final_spacing = docstring_sections.final_convention_section_spacing(docstring)
    if final_spacing is None or final_spacing.final_content_line is None or final_spacing.trailing_blank_line is None:
        return retained_lines
    if final_spacing.trailing_blank_line in retained_lines:
        return retained_lines
    # Rendering follows retained line order; this blank is after final section content, and any closing-quote prefix
    # line is appended later.
    return *retained_lines, final_spacing.trailing_blank_line


def _with_opening_quote_suffix_line(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> tuple[int, ...]:
    """Preserve an existing opening-quote suffix before content."""
    if not retained_lines:
        return retained_lines
    first_line = docstring.structure.lines[0]
    if not docstring_source.is_same_line_opening_delimiter_suffix(docstring, first_line):
        return retained_lines
    if retained_lines[0] == first_line.index:
        return retained_lines
    return first_line.index, *retained_lines


def _with_closing_quote_prefix_line(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> tuple[int, ...]:
    """Preserve an existing closing-quote prefix after content."""
    if not retained_lines:
        return retained_lines
    final_line = docstring.structure.lines[-1]
    if not docstring_source.is_same_line_closing_delimiter_prefix(docstring, final_line):
        return retained_lines
    if retained_lines[-1] == final_line.index:
        return retained_lines
    return *retained_lines, final_line.index
