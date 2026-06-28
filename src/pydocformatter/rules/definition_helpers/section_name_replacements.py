"""Preferred docstring section name lookup tables."""

from __future__ import annotations

import collections.abc as cabc

import pydocformatter.rules.definition_helpers.rest_fields as rest_fields
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.definition import RuleContext
from pydocformatter.rules.models import RuleMetadata

SectionNameMapper = cabc.Callable[[DocstringConvention, str], str | None]
FieldNameMapper = cabc.Callable[[str], str | None]
MessageBuilder = cabc.Callable[[str, str], str]


def results_for_mapped_names(
    context: RuleContext,
    *,
    rule: RuleMetadata,
    section_name_mapper: SectionNameMapper,
    section_message_builder: MessageBuilder,
    field_name_mapper: FieldNameMapper | None = None,
    field_message_builder: MessageBuilder | None = None,
) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for mapped docstring section and reStructuredText field names."""
    data = PDF_definition.PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for section in docstring.structure.sections:
            mapped_name = section_name_mapper(docstring.structure.convention, section.name)
            if mapped_name is None or mapped_name == section.name:
                continue
            message = section_message_builder(section.name, mapped_name)
            line = docstring.structure.lines[section.header_line]
            replacement = section_edits.replacement_for_section_name(line, section.name, mapped_name)
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                unfixable_messages.append(message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
            replacement_messages.append(message)
            section_edits.replace_value_line_span(value_lines, line, replacement, mapped_name)
        if field_name_mapper is not None and field_message_builder is not None:
            for entry in docstring.structure.entries:
                if entry.field_name is None:
                    continue
                line = docstring.structure.lines[entry.start_line]
                field_name = rest_fields.original_field_name(line)
                if field_name is None:
                    continue
                mapped_name = field_name_mapper(field_name)
                if mapped_name is None or mapped_name == field_name:
                    continue
                message = field_message_builder(field_name, mapped_name)
                replacement = rest_fields.replacement_for_field_name(line, mapped_name)
                if replacement is None:
                    unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                    unfixable_messages.append(message)
                    continue
                replacements.append(replacement)
                replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
                replacement_messages.append(message)
                section_edits.replace_value_line_span(value_lines, line, replacement, mapped_name)
        if not replacements and not unfixable_line_numbers:
            continue
        change = section_edits.planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(
            section_edits.replacement_results(
                rule,
                replacement_line_numbers=replacement_line_numbers,
                unfixable_line_numbers=unfixable_line_numbers,
                change=change,
                replacement_messages=replacement_messages,
                unfixable_messages=unfixable_messages,
            )
        )
    return tuple(results)
