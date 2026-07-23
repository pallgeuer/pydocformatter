"""Docstring section edit result helpers.

Attributes:
    SectionReplacementChange (TypeAlias): One source change or a grouped set of source changes backing a section
        replacement diagnostic.
"""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING, cast

# First-party imports
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext
    from pydocformatter.rules.definition_helpers import source_text, string_literals
    from pydocformatter.rules.models import RuleMetadata


SectionReplacementChange = rule_edits.PlannedSourceChange | tuple[rule_edits.PlannedSourceChange, ...]


def result(rule: RuleMetadata, line_numbers: tuple[int, ...] | list[int], *, change: rule_edits.PlannedSourceChange | None, instance_message: str | None = None) -> rule_violations.RuleViolation:
    """Return one section violation with deduplicated line numbers.

    Args:
        rule (RuleMetadata): Rule metadata to attach to the violation.
        line_numbers (tuple[int, ...] | list[int]): Source lines to report when no fix change is available.
        change (rule_edits.PlannedSourceChange | None): Optional source replacement for fixable section edits.
        instance_message (str | None): Optional message describing the concrete section issue.

    Returns:
        rule_violations.RuleViolation: Fixable or diagnostic-only section violation.
    """
    return rule_violations.violation_for_optional_planned_source_change(rule, change, line_numbers=tuple(dict.fromkeys(line_numbers)), instance_message=instance_message)


def replacement_results(
    rule: RuleMetadata,
    *,
    replacement_line_numbers: list[int],
    unfixable_line_numbers: list[int],
    change: SectionReplacementChange | None,
    replacement_messages: list[str],
    unfixable_messages: list[str],
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return section edit results for mixed fixable and unfixable replacements.

    Args:
        rule (RuleMetadata): Rule metadata to attach to all violations.
        replacement_line_numbers (list[int]): Lines covered by replacements that can share one source change.
        unfixable_line_numbers (list[int]): Lines where replacement spans could not be mapped safely.
        change (SectionReplacementChange | None): Source replacement or replacements for fixable section edits.
        replacement_messages (list[str]): Instance messages for fixable replacement lines.
        unfixable_messages (list[str]): Instance messages for diagnostic-only lines.

    Returns:
        tuple[rule_violations.RuleViolation, ...]: One fixable violation plus an optional unfixable violation, or a
            combined diagnostic when no change is available.
    """
    if not replacement_line_numbers:
        return (result(rule, unfixable_line_numbers, change=None, instance_message=combined_instance_message(unfixable_messages)),)
    if change is None:
        return (result(rule, tuple(replacement_line_numbers) + tuple(unfixable_line_numbers), change=None, instance_message=combined_instance_message(replacement_messages + unfixable_messages)),)
    results = [_result_for_replacement_change(rule, change, instance_message=combined_instance_message(replacement_messages))]
    if unfixable_line_numbers:
        results.append(result(rule, unfixable_line_numbers, change=None, instance_message=combined_instance_message(unfixable_messages)))
    return tuple(results)


def combined_instance_message(messages: list[str]) -> str | None:
    """Return a deduplicated semicolon-joined instance message.

    Args:
        messages (list[str]): Candidate instance messages collected while scanning one docstring.

    Returns:
        str | None: Stable combined message, or None when no concrete messages were provided.
    """
    if not messages:
        return None
    return "; ".join(dict.fromkeys(messages))


def _result_for_replacement_change(rule: RuleMetadata, change: SectionReplacementChange, *, instance_message: str | None) -> rule_violations.RuleViolation:
    """Return one violation for a single or grouped section replacement change."""
    if isinstance(change, rule_edits.PlannedSourceChange):
        return result(rule, change.line_numbers, change=change, instance_message=instance_message)
    return rule_violations.violation_for_grouped_planned_source_changes(rule, cast("tuple[rule_edits.PlannedSourceChange, ...]", change), instance_message=instance_message)


def line_numbers(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a docstring section line.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring that owns the value line.
        line (PDF_definition.DocstringValueLine): Parsed value line to map to physical source lines.

    Returns:
        tuple[int, ...]: One-based physical source lines occupied by the value line.
    """
    return PDF_definition.docstring_line_numbers(docstring, line)


def replacement_for_section_name(line: PDF_definition.DocstringValueLine, old_name: str, new_name: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for a section name span.

    Args:
        line (PDF_definition.DocstringValueLine): Value line containing the section header.
        old_name (str): Section name spelling expected at the start of the header.
        new_name (str): Replacement section name spelling.

    Returns:
        rule_edits.PlannedTextReplacement | None: Replacement for the section-name span, or None when source mapping is
            unsafe.
    """
    start_column = section_name_start_column(line)
    end_column = start_column + len(old_name)
    return text_replacement(line, start_column, end_column, new_name)


def replacement_for_section_suffix(line: PDF_definition.DocstringValueLine, name: str, suffix: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for the suffix after a section name.

    Args:
        line (PDF_definition.DocstringValueLine): Value line containing the section header.
        name (str): Section name whose trailing text should be replaced.
        suffix (str): Replacement text after the section name.

    Returns:
        rule_edits.PlannedTextReplacement | None: Replacement for the suffix span, or None when source mapping is
            unsafe.
    """
    start_column = section_name_start_column(line) + len(name)
    end_column = len(line.text)
    return text_replacement(line, start_column, end_column, suffix)


def text_replacement(line: PDF_definition.DocstringValueLine, start_column: int, end_column: int, text: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a value-line text replacement when source mapping is exact.

    Args:
        line (PDF_definition.DocstringValueLine): Parsed value line whose source offsets should be mapped.
        start_column (int): Text-column start of the replacement span.
        end_column (int): Text-column end of the replacement span.
        text (str): Replacement text to write into the mapped source span.

    Returns:
        rule_edits.PlannedTextReplacement | None: Source-offset replacement, or None when the value columns cannot be
            mapped exactly.
    """
    start_offset = PDF_definition.value_offset_for_text_column(line, start_column, require_source_text=True)
    end_offset = PDF_definition.value_offset_for_text_column(line, end_column, require_source_text=True)
    if start_offset is None or end_offset is None:
        return None
    return rule_edits.PlannedTextReplacement(start_offset=start_offset, end_offset=end_offset, text=text, line_numbers=PDF_definition.docstring_value_line_numbers((line,)))


def section_name_start_column(line: PDF_definition.DocstringValueLine) -> int:
    """Return the text column where a section name starts.

    Args:
        line (PDF_definition.DocstringValueLine): Value line containing the section header.

    Returns:
        int: First non-whitespace text column in the value line.
    """
    return len(line.text) - len(line.text.lstrip(" \t"))


def replace_value_line_span(value_lines: list[str], line: PDF_definition.DocstringValueLine, replacement: rule_edits.PlannedTextReplacement, text: str) -> None:
    """Apply a replacement to copied raw value lines.

    Args:
        value_lines (list[str]): Mutable raw value-line copy used to build a whole-docstring replacement.
        line (PDF_definition.DocstringValueLine): Parsed value line whose index selects the copied line.
        replacement (rule_edits.PlannedTextReplacement): Source-offset replacement already mapped within `line`.
        text (str): Replacement text to splice into the copied value line.
    """
    raw_start_column = replacement.start_offset - line.start_offset
    raw_end_column = replacement.end_offset - line.start_offset
    value_lines[line.index] = f"{value_lines[line.index][:raw_start_column]}{text}{value_lines[line.index][raw_end_column:]}"


def planned_replacement_change(
    docstring: PDF_definition.DocstringInfo, *, replacements: tuple[rule_edits.PlannedTextReplacement, ...], value_lines: list[str]
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe whole-docstring replacement for section text replacements.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to replace as a whole source literal.
        replacements (tuple[rule_edits.PlannedTextReplacement, ...]): Text replacements that determine diagnostic lines.
        value_lines (list[str]): Updated raw value lines for the replacement docstring body.

    Returns:
        rule_edits.PlannedSourceChange | None: Whole-docstring replacement, or None when the docstring cannot be mapped
            safely.
    """
    if not replacements or not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_source_change(docstring, replacements=replacements, value_lines=value_lines)


def planned_replacement_changes(
    docstring: PDF_definition.DocstringInfo, *, context: RuleContext, replacements: tuple[rule_edits.PlannedTextReplacement, ...], value_lines: list[str]
) -> SectionReplacementChange | None:
    """Return direct section source replacements with a whole-docstring fallback.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring whose section text should be replaced.
        context (RuleContext): Current file context used to build source edits.
        replacements (tuple[rule_edits.PlannedTextReplacement, ...]): Text replacements that determine diagnostic lines.
        value_lines (list[str]): Updated raw value lines for the fallback replacement docstring body.

    Returns:
        SectionReplacementChange | None: Direct source replacements, one whole-docstring replacement, or None when the
            docstring cannot be mapped safely.
    """
    direct_changes = _direct_replacement_changes(docstring, context=context, replacements=replacements)
    if direct_changes is not None:
        return direct_changes
    return planned_replacement_change(docstring, replacements=replacements, value_lines=value_lines)


def _direct_replacement_changes(
    docstring: PDF_definition.DocstringInfo, *, context: RuleContext, replacements: tuple[rule_edits.PlannedTextReplacement, ...]
) -> tuple[rule_edits.PlannedSourceChange, ...] | None:
    """Return line-local source replacements when every replacement maps directly."""
    if not replacements:
        return None
    line_bounds = PDF_definition.line_bounds_for_context(context)
    source_map = docstring.source_map
    if source_map is None:
        return None
    changes: list[rule_edits.PlannedSourceChange] = []
    previous_line = 0
    previous_end_column = -1
    for replacement in replacements:
        change = _direct_replacement_change(docstring, replacement=replacement, source_map=source_map, line_bounds=line_bounds)
        if change is None:
            return None
        start = change.edit.range.start
        end = change.edit.range.end
        if start.line < previous_line or (start.line == previous_line and start.column < previous_end_column):
            return None
        previous_line = end.line
        previous_end_column = end.column
        changes.append(change)
    return tuple(changes)


def _direct_replacement_change(
    docstring: PDF_definition.DocstringInfo, *, replacement: rule_edits.PlannedTextReplacement, source_map: string_literals.SimpleStringSourceMap, line_bounds: source_text.LineBounds
) -> rule_edits.PlannedSourceChange | None:
    """Return one line-local section edit when source spelling matches raw value text."""
    line = _line_for_replacement(docstring, replacement)
    if line is None or line.source_line_number is None:
        return None
    raw_start_column = replacement.start_offset - line.start_offset
    raw_end_column = replacement.end_offset - line.start_offset
    if replacement.start_offset < 0 or replacement.end_offset < replacement.start_offset or replacement.end_offset > len(source_map.value):
        return None
    if not PDF_definition.simple_docstring_replacement_is_source_safe(docstring, replacement.text):
        return None
    expected_source = line.raw_text[raw_start_column:raw_end_column]
    if source_map.producing_source_for_value_slice(replacement.start_offset, replacement.end_offset) != expected_source:
        return None
    return rule_edits.PlannedSourceChange(
        edit=rule_edits.SourceEdit(
            range=PDF_definition.simple_docstring_source_range(docstring, source_map=source_map, start_offset=replacement.start_offset, end_offset=replacement.end_offset, line_bounds=line_bounds),
            replacement=replacement.text,
        ),
        line_numbers=replacement.line_numbers,
        suppression_line_numbers=(),
    )


def _line_for_replacement(docstring: PDF_definition.DocstringInfo, replacement: rule_edits.PlannedTextReplacement) -> PDF_definition.DocstringValueLine | None:
    """Return the docstring value line fully covered by one replacement."""
    return next((line for line in docstring.structure.lines if line.start_offset <= replacement.start_offset <= replacement.end_offset <= line.end_offset), None)


def planned_output_change(
    docstring: PDF_definition.DocstringInfo, *, context: RuleContext, output_lines: tuple[PDF_definition.DocstringOutputLine, ...], line_numbers: tuple[int, ...]
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe whole-docstring replacement for section output lines.

    Args:
        docstring (PDF_definition.DocstringInfo): Parsed docstring to replace as a whole source literal.
        context (RuleContext): Current file context used to build source edits.
        output_lines (tuple[PDF_definition.DocstringOutputLine, ...]): Rendered docstring value lines for replacement.
        line_numbers (tuple[int, ...]): Diagnostic lines associated with the replacement.

    Returns:
        rule_edits.PlannedSourceChange | None: Whole-docstring replacement, or None when the docstring cannot be mapped
            safely.
    """
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers)
