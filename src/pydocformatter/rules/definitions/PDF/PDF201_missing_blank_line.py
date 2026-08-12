"""PDF201 missing-blank-line rule."""

# Future imports
from __future__ import annotations

# Standard library imports
import itertools
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
class PDF201MissingBlankLine(RuleBase):
    """Rule implementation for PDF201.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF201"),
        name="missing-blank-line",
        message="Docstring is missing a blank line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for safely insertable missing blank lines.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe missing blank-line insertions."""
    data = PDF_definition.PDF.require_data(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not docstring_source.can_canonically_rewrite_simple_docstring(docstring):
        return None
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    insert_before = _insertions_before_lines(docstring)
    insert_after = _insertions_after_lines(docstring, context=context)
    if not insert_before and not insert_after:
        return None
    canonical_margin = docstring_source.docstring_canonical_margin(docstring, context=context)
    blank_source = _blank_line_source(context, canonical_margin=canonical_margin)
    output_lines, line_numbers = _output_lines_and_line_numbers(docstring, insert_before=insert_before, insert_after=insert_after, blank_source=blank_source, canonical_margin=canonical_margin)
    return docstring_rendering.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=tuple(dict.fromkeys(line_numbers)))


def _insertions_before_lines(docstring: PDF_definition.DocstringInfo) -> frozenset[int]:
    """Return logical line indexes before which a blank line should be inserted."""
    indexes: set[int] = set()
    blocks = docstring.structure.blocks
    for previous_block, block in itertools.pairwise(blocks):
        if previous_block.kind is PDF_definition.DocstringBlockKind.BLANK or block.kind is PDF_definition.DocstringBlockKind.BLANK:
            continue
        if _previous_logical_line_is_blank(docstring, block.start_line):
            continue
        if _needs_blank_before_block(previous_block, block):
            indexes.add(block.start_line)
    return frozenset(indexes)


def _insertions_after_lines(docstring: PDF_definition.DocstringInfo, *, context: RuleContext) -> frozenset[int]:
    """Return logical line indexes after which a blank line should be inserted."""
    if not context.settings.docstring_blank_line_after_last_section:
        return frozenset[int]()
    final_spacing = docstring_sections.final_convention_section_spacing(docstring)
    if final_spacing is None or final_spacing.final_content_line is None:
        return frozenset[int]()
    if final_spacing.trailing_blank_line is not None:
        return frozenset[int]()
    return frozenset({final_spacing.final_content_line})


def _needs_blank_before_block(previous_block: PDF_definition.DocstringBlock, block: PDF_definition.DocstringBlock) -> bool:
    """Return whether adjacent top-level blocks require a blank separator."""
    if block.kind is PDF_definition.DocstringBlockKind.SECTION:
        return True
    return bool(previous_block.kind is PDF_definition.DocstringBlockKind.SUMMARY and previous_block.end_line - previous_block.start_line == 1 and _is_recognized_structure(block))


def _previous_logical_line_is_blank(docstring: PDF_definition.DocstringInfo, line_index: int) -> bool:
    """Return whether the line immediately before an index is blank."""
    return line_index > 0 and not docstring.structure.lines[line_index - 1].text.strip()


def _is_recognized_structure(block: PDF_definition.DocstringBlock) -> bool:
    """Return whether a block is structured enough to safely separate from a summary."""
    return block.kind in {
        PDF_definition.DocstringBlockKind.SECTION,
        PDF_definition.DocstringBlockKind.COLON_HEADER,
        PDF_definition.DocstringBlockKind.LIST_ITEM,
        PDF_definition.DocstringBlockKind.HEADING,
        PDF_definition.DocstringBlockKind.DOCTEST,
        PDF_definition.DocstringBlockKind.CODE_FENCE,
        PDF_definition.DocstringBlockKind.BLOCK_QUOTE,
        PDF_definition.DocstringBlockKind.TABLE,
        PDF_definition.DocstringBlockKind.DIRECTIVE,
        PDF_definition.DocstringBlockKind.DIRECTIVE_ISSUE,
        PDF_definition.DocstringBlockKind.LITERAL_BLOCK,
        PDF_definition.DocstringBlockKind.REST_FIELD,
        PDF_definition.DocstringBlockKind.VERBATIM,
    }


def _blank_line_source(context: RuleContext, *, canonical_margin: str) -> str:
    """Return source text for a generated blank line."""
    if context.settings.docstring_blank_line_style == settings_check.DocstringBlankLineStyle.ALIGNED:
        return canonical_margin
    return ""


def _output_lines_and_line_numbers(
    docstring: PDF_definition.DocstringInfo, *, insert_before: frozenset[int], insert_after: frozenset[int], blank_source: str, canonical_margin: str
) -> tuple[tuple[docstring_rendering.DocstringOutputLine, ...], tuple[int, ...]]:
    """Return replacement logical lines and changed source line numbers."""
    lines: list[docstring_rendering.DocstringOutputLine] = []
    line_numbers: list[int] = []
    for line in docstring.structure.lines:
        if line.index in insert_before:
            lines.append(docstring_rendering.DocstringOutputLine(source=blank_source, value=blank_source))
            if line.source_line_number is not None:
                line_numbers.append(line.source_line_number)
        lines.append(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None))
        if line.index in insert_after:
            lines.append(docstring_rendering.DocstringOutputLine(source=blank_source, value=blank_source))
            if line.source_line_number is not None:
                line_numbers.append(line.source_line_number)
            if line.index == len(docstring.structure.lines) - 1 and not docstring_source.docstring_value_ends_with_newline(docstring):
                lines.append(docstring_rendering.DocstringOutputLine(source=canonical_margin, value=canonical_margin))
    return tuple(lines), tuple(line_numbers)
