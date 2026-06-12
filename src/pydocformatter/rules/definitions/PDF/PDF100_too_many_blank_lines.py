from __future__ import annotations

import libcst as cst

import pydocformatter.rules.definition_helpers.string_literals as string_literals
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF100TooManyBlankLines(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF100"),
        name="too-many-blank-lines",
        message="Docstring has too many blank lines",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
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
    source_lines = PDF_definition.source_lines_from_context(context)
    return tuple(change for docstring in data.docstrings if (change := _planned_change_for_docstring(docstring, context=context, source_lines=source_lines)) is not None)


def _planned_change_for_docstring(docstring: PDF_definition.DocstringInfo, *, context: RuleContext, source_lines: list[str]) -> rule_edits.PlannedSourceChange | None:
    """Return one whole-literal replacement for a docstring."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    # Narrow for typing after the safe-mapping predicate.
    if not isinstance(docstring.node, cst.SimpleString):
        return None
    retained_lines = _retained_line_indexes(docstring.structure.blocks)
    if retained_lines is None:
        retained_lines = ()
    else:
        canonical_margin = PDF_definition.docstring_canonical_margin(docstring, context=context, source_lines=source_lines)
        retained_lines = _with_closing_quote_prefix_line(docstring, retained_lines, canonical_margin=canonical_margin)
    retained_line_set = set(retained_lines)
    changed_line_numbers = tuple(line.source_line_number for line in docstring.structure.lines if line.index not in retained_line_set and line.source_line_number is not None)
    if not changed_line_numbers:
        return None
    fragments = PDF_definition.docstring_value_fragments(docstring, line_ending=context.line_ending)
    if fragments is None:
        return None
    body_source = _body_source(docstring, retained_lines, fragments=fragments, line_ending=context.line_ending)
    expected_value = _expected_value(docstring, retained_lines)
    rendered = string_literals.render_simple_string_from_body_source(docstring.node.prefix, docstring.node.quote, body_source, expected_value=expected_value)
    if rendered is None or rendered == docstring.source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(range=docstring.range, replacement=rendered),
        line_numbers=changed_line_numbers,
    )


def _retained_line_indexes(blocks: tuple[PDF_definition.DocstringBlock, ...]) -> tuple[int, ...] | None:
    """Return retained logical lines, or None if a blank-only range becomes empty."""
    if not blocks:
        return ()
    non_blank_indexes = tuple(index for index, block in enumerate(blocks) if block.kind is not PDF_definition.DocstringBlockKind.BLANK)
    if not non_blank_indexes:
        return None

    retained: list[int] = []
    first_chunk = non_blank_indexes[0]
    last_chunk = non_blank_indexes[-1]
    for block in blocks[first_chunk : last_chunk + 1]:
        if block.kind is PDF_definition.DocstringBlockKind.BLANK:
            retained.append(block.start_line)
            continue
        child_lines = _retained_line_indexes(block.children)
        if child_lines is None:
            child_lines = ()
        if child_lines:
            retained.extend(child_lines)
        else:
            retained.extend(range(block.start_line, block.end_line))
    return tuple(retained)


def _body_source(
    docstring: PDF_definition.DocstringInfo,
    retained_lines: tuple[int, ...],
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
    line_ending: str,
) -> str:
    """Return replacement literal body source for retained logical lines."""
    if not retained_lines:
        return ""
    lines = docstring.structure.lines
    chunks: list[str] = []
    for output_index, line_index in enumerate(retained_lines):
        if output_index:
            chunks.append(line_ending)
        line = lines[line_index]
        chunks.append(_line_source(line, fragments=fragments, strip_docstring_margin=output_index == 0))
    if _preserve_trailing_newline(docstring, retained_lines):
        chunks.append(line_ending)
    return "".join(chunks)


def _expected_value(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> str:
    """Return replacement evaluated docstring value."""
    if not retained_lines:
        return ""
    lines = docstring.structure.lines
    chunks: list[str] = []
    for output_index, line_index in enumerate(retained_lines):
        if output_index:
            chunks.append("\n")
        chunks.append(lines[line_index].text if output_index == 0 else lines[line_index].raw_text)
    if _preserve_trailing_newline(docstring, retained_lines):
        chunks.append("\n")
    return "".join(chunks)


def _preserve_trailing_newline(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...]) -> bool:
    """Return whether a trailing evaluated newline should remain before closing quotes."""
    if not retained_lines:
        return False
    return docstring.value.endswith(("\r\n", "\r", "\n"))


def _with_closing_quote_prefix_line(docstring: PDF_definition.DocstringInfo, retained_lines: tuple[int, ...], *, canonical_margin: str) -> tuple[int, ...]:
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
    return (*retained_lines, final_line.index)


def _line_source(
    line: PDF_definition.DocstringValueLine,
    *,
    fragments: tuple[string_literals.StringValueFragment, ...],
    strip_docstring_margin: bool,
) -> str:
    """Return source spelling for a retained logical line."""
    if not strip_docstring_margin:
        return string_literals.source_for_value_slice(fragments, line.start_offset, line.end_offset)
    start_offset = line.start_offset + line.text_raw_start_column
    return f"{' ' * line.text_virtual_prefix_length}{string_literals.source_for_value_slice(fragments, start_offset, line.end_offset)}"
