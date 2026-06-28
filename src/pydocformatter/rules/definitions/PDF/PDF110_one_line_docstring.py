"""PDF110 one-line-docstring rule."""

from __future__ import annotations

from collections.abc import Sequence

import pydocformatter.rules.definition_helpers.text_layout as text_layout
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF110OneLineDocstring(RuleBase):
    """Rule implementation for PDF110.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF110"),
        name="one-line-docstring",
        message="Docstring with one content line should be one line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summary-only docstrings that should be collapsed."""
        return rule_violations.violations_for_planned_source_changes(cls.meta, _planned_changes(context))


def _planned_changes(context: RuleContext) -> tuple[rule_edits.PlannedSourceChange, ...]:
    """Return all safe one-line docstring collapses."""
    data = PDF_definition.PDF.require_data(context)
    source_lines = context.source_lines
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: Sequence[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a summary-only docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring, require_multiline=True):
        return None
    summary_line = _single_summary_line(docstring)
    if summary_line is None:
        return None
    rendered = _rendered_one_line_docstring(docstring, summary_line, context=context)
    if rendered is None or rendered == docstring.source:
        return None
    if not _rendered_line_fits(docstring, rendered, context=context, source_lines=source_lines):
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=tuple(line.line_number for line in docstring.physical_lines),
        suppression_line_numbers=(),
    )


def _single_summary_line(docstring: PDF_definition.DocstringInfo) -> PDF_definition.DocstringValueLine | None:
    """Return the only summary line if the docstring contains only one summary line."""
    non_blank_blocks = tuple(block for block in docstring.structure.blocks if block.kind is not PDF_definition.DocstringBlockKind.BLANK)
    if len(non_blank_blocks) != 1:
        return None
    block = non_blank_blocks[0]
    if block.kind is not PDF_definition.DocstringBlockKind.SUMMARY or block.end_line - block.start_line != 1:
        return None
    return docstring.structure.lines[block.start_line]


def _rendered_one_line_docstring(docstring: PDF_definition.DocstringInfo, summary_line: PDF_definition.DocstringValueLine, *, context: RuleContext) -> str | None:
    """Return one-line source for a docstring while preserving safe source spelling."""
    fragments = PDF_definition.docstring_value_fragments(docstring, line_ending=context.line_ending)
    if fragments is None:
        return None
    strip_docstring_margin = summary_line.index != 0
    body_source = PDF_definition.docstring_line_source(summary_line, fragments=fragments, strip_docstring_margin=strip_docstring_margin)
    expected_value = summary_line.text if strip_docstring_margin else summary_line.raw_text
    return PDF_definition.render_simple_docstring_body_with_separator_fallbacks(docstring, body_source=body_source, expected_value=expected_value)


def _rendered_line_fits(docstring: PDF_definition.DocstringInfo, rendered: str, *, context: RuleContext, source_lines: Sequence[str]) -> bool:
    """Return whether the replacement keeps the resulting physical source line within line length."""
    start_line = source_lines[docstring.range.start.line - 1].rstrip("\r\n")
    end_line = source_lines[docstring.range.end.line - 1].rstrip("\r\n")
    line = f"{start_line[: docstring.range.start.column]}{rendered}{end_line[docstring.range.end.column :]}"
    return text_layout.display_width(line, tab_width=context.settings.indent_width) <= context.settings.line_length
