from __future__ import annotations

import libcst as cst

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.source_text as source_text
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF200TooManyBlankLines(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF200"),
        name="too-many-blank-lines",
        message="Docstring has too many blank lines",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for excess blank lines in docstrings."""
        return rule_edits.findings_for_planned_source_changes(cls.meta, _planned_changes(context))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Collapse excess blank lines in docstrings."""
        changes = _planned_changes(context)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_planned_source_changes(context.module, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes)
        return RuleFixResult(module=module, fixed_findings=findings)


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe blank-line collapse changes."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = source_text.source_lines_from_context(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    # Narrow for typing after the safe-mapping predicate.
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    retained_lines = _retained_line_indexes(docstring.structure.blocks, convention=docstring.structure.convention)
    output_lines: tuple[PDF_definition.DocstringOutputLine, ...]
    if retained_lines is None:
        retained_lines = ()
        output_lines = ()
    else:
        canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
        retained_lines = _with_configured_final_section_blank(docstring, retained_lines, context=context)
        retained_lines = _with_closing_quote_prefix_line(
            docstring, retained_lines, canonical_margin=canonical_margin, keep_final_section_blank=context.settings.docstring_blank_line_after_last_section
        )
        output_lines = _output_lines(docstring, retained_lines)
    retained_line_set = set(retained_lines)
    changed_line_numbers = tuple(line.source_line_number for line in docstring.structure.lines if line.index not in retained_line_set and line.source_line_number is not None)
    if not changed_line_numbers:
        return None
    return PDF_definition.planned_simple_docstring_output_change(
        docstring,
        context=context,
        output_lines=output_lines,
        line_numbers=changed_line_numbers,
        preserve_trailing_newline=bool(retained_lines) and PDF_definition.docstring_value_ends_with_newline(docstring),
    )


def _retained_line_indexes(
    blocks: tuple[PDF_definition.DocstringBlock, ...],
    *,
    convention: settings_check.DocstringConvention,
    parent_kind: PDF_definition.DocstringBlockKind | None = None,
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


def _keeps_blank_separator_after_section(
    block: PDF_definition.DocstringBlock,
    next_block: PDF_definition.DocstringBlock | None,
    *,
    convention: settings_check.DocstringConvention,
) -> bool:
    """Return whether a section trailing blank separates it from another section."""
    return (
        convention in (settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.NUMPY)
        and block.kind is PDF_definition.DocstringBlockKind.SECTION
        and next_block is not None
        and next_block.kind is PDF_definition.DocstringBlockKind.SECTION
        and _trailing_blank_line(block) is not None
    )


def _trailing_blank_line(block: PDF_definition.DocstringBlock) -> int | None:
    """Return the first trailing blank line in a block."""
    trailing_blank = block.children[-1] if block.children and block.children[-1].kind is PDF_definition.DocstringBlockKind.BLANK else None
    return None if trailing_blank is None else trailing_blank.start_line


def _output_lines(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> tuple[PDF_definition.DocstringOutputLine, ...]:
    """Return replacement logical lines for retained docstring indexes."""
    return tuple(
        PDF_definition.DocstringOutputLine(original=line, strip_docstring_margin=output_index == 0 and line.index != 0)
        for output_index, line_index in enumerate(retained_lines)
        for line in (docstring.structure.lines[line_index],)
    )


def _with_configured_final_section_blank(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...], *, context: RuleContext) -> tuple[int, ...]:
    """Preserve one trailing blank after the final convention section when configured."""
    if not context.settings.docstring_blank_line_after_last_section:
        return retained_lines
    final_spacing = PDF_definition.final_convention_section_spacing(docstring)
    if final_spacing is None or final_spacing.final_content_line is None or final_spacing.trailing_blank_line is None:
        return retained_lines
    if final_spacing.trailing_blank_line in retained_lines:
        return retained_lines
    # Rendering follows retained line order; this blank is after final section content, and any closing-quote prefix
    # line is appended later.
    return *retained_lines, final_spacing.trailing_blank_line


def _with_closing_quote_prefix_line(
    docstring: PDF_definition.DocstringInfo,
    retained_lines: tuple[int, ...],
    *,
    canonical_margin: str,
    keep_final_section_blank: bool,
) -> tuple[int, ...]:
    """Preserve a final same-line closing-quote prefix after content."""
    if not retained_lines:
        return retained_lines
    final_line = docstring.structure.lines[-1]
    if not PDF_definition.is_same_line_closing_delimiter_prefix(docstring, final_line):
        return retained_lines
    if final_line.raw_text != canonical_margin:
        return retained_lines
    if retained_lines[-1] == final_line.index:
        return retained_lines
    if not keep_final_section_blank and _is_final_section_trailing_blank(docstring, final_line.index):
        return retained_lines
    return *retained_lines, final_line.index


def _is_final_section_trailing_blank(docstring: PDF_definition.DocstringInfo, line_index: int) -> bool:
    """Return whether a line is a blank immediately after the final convention section."""
    final_spacing = PDF_definition.final_convention_section_spacing(docstring)
    return final_spacing is not None and final_spacing.section.end_line == line_index
