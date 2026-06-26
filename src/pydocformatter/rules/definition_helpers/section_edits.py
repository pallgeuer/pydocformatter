"""Docstring section edit result helpers."""

from __future__ import annotations

import dataclasses

import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition import RuleContext, RuleFixResult
from pydocformatter.rules.models import RuleFinding, RuleMetadata


@dataclasses.dataclass(frozen=True)
class SectionEditResult:
    """A section-style finding and its optional whole-docstring change.

    Attributes:
        finding (RuleFinding): Diagnostic reported for the section-style issue.
        change (rule_edits.PlannedSourceChange | None): Whole-docstring edit that fixes the issue, if available.
    """

    finding: RuleFinding
    change: rule_edits.PlannedSourceChange | None


def findings_for_results(results: tuple[SectionEditResult, ...]) -> tuple[RuleFinding, ...]:
    """Return findings from section edit results."""
    return tuple(result.finding for result in results)


def fix_result_for_results(context: RuleContext, rule: RuleMetadata, results: tuple[SectionEditResult, ...]) -> RuleFixResult:
    """Apply planned section changes and return fixed findings."""
    changes = tuple(result.change for result in results if result.change is not None)
    if not changes:
        return RuleFixResult(module=context.module)
    return rule_edits.fix_result_for_planned_source_changes(context, rule, changes, instance_fixable=True)


def result(rule: RuleMetadata, line_numbers: tuple[int, ...] | list[int], *, change: rule_edits.PlannedSourceChange | None, instance_message: str | None = None) -> SectionEditResult:
    """Return one section edit result with deduplicated line numbers."""
    return SectionEditResult(finding=RuleFinding(rule=rule, line_numbers=tuple(dict.fromkeys(line_numbers)), instance_fixable=change is not None, instance_message=instance_message), change=change)


def replacement_results(
    rule: RuleMetadata,
    *,
    replacement_line_numbers: list[int],
    unfixable_line_numbers: list[int],
    change: rule_edits.PlannedSourceChange | None,
    replacement_messages: list[str],
    unfixable_messages: list[str],
) -> tuple[SectionEditResult, ...]:
    """Return section edit results for mixed fixable and unfixable replacements."""
    if not replacement_line_numbers:
        return (result(rule, unfixable_line_numbers, change=None, instance_message=combined_instance_message(unfixable_messages)),)
    if change is None:
        return (
            result(
                rule,
                tuple(replacement_line_numbers) + tuple(unfixable_line_numbers),
                change=None,
                instance_message=combined_instance_message(replacement_messages + unfixable_messages),
            ),
        )
    results = [result(rule, change.line_numbers, change=change, instance_message=combined_instance_message(replacement_messages))]
    if unfixable_line_numbers:
        results.append(result(rule, unfixable_line_numbers, change=None, instance_message=combined_instance_message(unfixable_messages)))
    return tuple(results)


def combined_instance_message(messages: list[str]) -> str | None:
    """Return a deduplicated semicolon-joined instance message."""
    if not messages:
        return None
    return "; ".join(dict.fromkeys(messages))


def line_numbers(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> tuple[int, ...]:
    """Return concrete source lines for a docstring section line."""
    return PDF_definition.docstring_line_numbers(docstring, line)


def replacement_for_section_name(line: PDF_definition.DocstringValueLine, old_name: str, new_name: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for a section name span."""
    start_column = section_name_start_column(line)
    end_column = start_column + len(old_name)
    return text_replacement(line, start_column, end_column, new_name)


def replacement_for_section_suffix(line: PDF_definition.DocstringValueLine, name: str, suffix: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a replacement for the suffix after a section name."""
    start_column = section_name_start_column(line) + len(name)
    end_column = len(line.text)
    return text_replacement(line, start_column, end_column, suffix)


def text_replacement(line: PDF_definition.DocstringValueLine, start_column: int, end_column: int, text: str) -> rule_edits.PlannedTextReplacement | None:
    """Return a value-line text replacement when source mapping is exact."""
    start_offset = PDF_definition.value_offset_for_text_column(line, start_column, require_source_text=True)
    end_offset = PDF_definition.value_offset_for_text_column(line, end_column, require_source_text=True)
    if start_offset is None or end_offset is None:
        return None
    return rule_edits.PlannedTextReplacement(start_offset=start_offset, end_offset=end_offset, text=text, line_numbers=PDF_definition.docstring_value_line_numbers((line,)))


def section_name_start_column(line: PDF_definition.DocstringValueLine) -> int:
    """Return the text column where a section name starts."""
    return len(line.text) - len(line.text.lstrip(" \t"))


def replace_value_line_span(value_lines: list[str], line: PDF_definition.DocstringValueLine, replacement: rule_edits.PlannedTextReplacement, text: str) -> None:
    """Apply a replacement to copied raw value lines."""
    raw_start_column = replacement.start_offset - line.start_offset
    raw_end_column = replacement.end_offset - line.start_offset
    value_lines[line.index] = f"{value_lines[line.index][:raw_start_column]}{text}{value_lines[line.index][raw_end_column:]}"


def planned_replacement_change(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    replacements: tuple[rule_edits.PlannedTextReplacement, ...],
    value_lines: list[str],
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe whole-docstring replacement for section text replacements."""
    if not replacements or not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_source_change(docstring, context=context, replacements=replacements, value_lines=value_lines)


def planned_output_change(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    output_lines: tuple[PDF_definition.DocstringOutputLine, ...],
    line_numbers: tuple[int, ...],
) -> rule_edits.PlannedSourceChange | None:
    """Return a safe whole-docstring replacement for section output lines."""
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers)
