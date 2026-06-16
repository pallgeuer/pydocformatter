from __future__ import annotations

import dataclasses
import re

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.edits as rule_edits
from pydocformatter.rules.definition import RuleContext, RuleFixResult
from pydocformatter.rules.models import RuleFinding, RuleMetadata

GOOGLE_IGNORED_CONVENTIONS = (settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.NUMPY, settings_check.DocstringConvention.PEP257)
NUMPY_IGNORED_CONVENTIONS = (settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.GOOGLE, settings_check.DocstringConvention.PEP257)
SECTION_IGNORED_CONVENTIONS = (settings_check.DocstringConvention.NONE, settings_check.DocstringConvention.PEP257)

_GOOGLE_TRAILING_CONTENT_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<name>[A-Za-z][A-Za-z ]*?)[ \t]*:[ \t]+(?P<content>\S.*)$")


@dataclasses.dataclass(frozen=True)
class SectionStyleResult:
    """A section-style finding and its optional whole-docstring change."""

    finding: RuleFinding
    change: rule_edits.PlannedSourceChange | None


def canonical_section_name(convention: settings_check.DocstringConvention, name: str) -> str | None:
    """Return the canonical spelling for a recognized section name."""
    return PDF_definition.canonical_section_name(convention, name)


def findings_for_results(results: tuple[SectionStyleResult, ...]) -> tuple[RuleFinding, ...]:
    """Return findings from section-style results."""
    return tuple(result.finding for result in results)


def fix_result_for_results(context: RuleContext, rule: RuleMetadata, results: tuple[SectionStyleResult, ...]) -> RuleFixResult:
    """Apply planned section-style changes and return fixed findings."""
    changes = tuple(result.change for result in results if result.change is not None)
    if not changes:
        return RuleFixResult(module=context.module)
    module = rule_edits.apply_planned_source_changes(context.module, changes)
    findings = rule_edits.findings_for_planned_source_changes(rule, changes, instance_fixable=True)
    return RuleFixResult(module=module, fixed_findings=findings)


def capitalization_results(context: RuleContext, *, rule: RuleMetadata) -> tuple[SectionStyleResult, ...]:
    """Return findings and fixes for section name capitalization."""
    data = PDF_definition.PDF.require_data(context)
    results: list[SectionStyleResult] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        for section in docstring.structure.sections:
            canonical = canonical_section_name(docstring.structure.convention, section.name)
            if canonical is None or canonical == section.name:
                continue
            line = docstring.structure.lines[section.header_line]
            replacement = _replacement_for_section_name(line, section.name, canonical)
            if replacement is None:
                unfixable_line_numbers.extend(_line_numbers(docstring, line))
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(_line_numbers(docstring, line))
            _replace_value_line_span(value_lines, line, replacement, canonical)
        if not replacements and not unfixable_line_numbers:
            continue
        change = _planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(_replacement_results(rule, replacement_line_numbers=replacement_line_numbers, unfixable_line_numbers=unfixable_line_numbers, change=change))
    return tuple(results)


def trailing_content_results(context: RuleContext, *, rule: RuleMetadata) -> tuple[SectionStyleResult, ...]:
    """Return findings and fixes for section names followed by trailing content."""
    data = PDF_definition.PDF.require_data(context)
    results: list[SectionStyleResult] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not settings_check.DocstringConvention.GOOGLE:
            continue
        output_lines: list[PDF_definition.DocstringOutputLine] = []
        line_numbers: list[int] = []
        protected_indexes = _protected_or_parsed_line_indexes(docstring)
        changed = False
        for line in docstring.structure.lines:
            target = None if line.index in protected_indexes else _google_trailing_content_target(line, context=context)
            if target is None:
                output_lines.append(PDF_definition.DocstringOutputLine(original=line))
                continue
            header, content = target
            line_numbers.extend(_line_numbers(docstring, line))
            output_lines.append(PDF_definition.DocstringOutputLine(source=header, value=header))
            output_lines.append(PDF_definition.DocstringOutputLine(source=content, value=content))
            changed = True
        if not changed:
            continue
        change = _planned_output_change(docstring, context=context, output_lines=tuple(output_lines), line_numbers=tuple(line_numbers))
        results.append(_result(rule, line_numbers, change=change))
    return tuple(results)


def underline_results(context: RuleContext, *, rule: RuleMetadata) -> tuple[SectionStyleResult, ...]:
    """Return findings and fixes for NumPy section underlines."""
    data = PDF_definition.PDF.require_data(context)
    results: list[SectionStyleResult] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not settings_check.DocstringConvention.NUMPY:
            continue
        output_lines: list[PDF_definition.DocstringOutputLine] = []
        line_numbers: list[int] = []
        section_by_header = {section.header_line: section for section in docstring.structure.sections}
        skip_indexes: set[int] = set()
        changed = False
        for line in docstring.structure.lines:
            if line.index in skip_indexes:
                changed = True
                continue
            section = section_by_header.get(line.index)
            if section is None:
                output_lines.append(PDF_definition.DocstringOutputLine(original=line))
                continue
            output_lines.append(PDF_definition.DocstringOutputLine(original=line))
            underline, skipped = _target_underline(docstring, section)
            if underline is None:
                continue
            line_numbers.extend(_line_numbers(docstring, line))
            output_lines.append(PDF_definition.DocstringOutputLine(source=underline, value=underline))
            skip_indexes.update(skipped)
            changed = True
        if not changed:
            continue
        change = _planned_output_change(docstring, context=context, output_lines=tuple(output_lines), line_numbers=tuple(line_numbers))
        results.append(_result(rule, line_numbers, change=change))
    return tuple(results)


def empty_section_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for recognized sections with no body content."""
    data = PDF_definition.PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        for section in docstring.structure.sections:
            if not _section_has_content(docstring, section):
                line = docstring.structure.lines[section.header_line]
                findings.append(RuleFinding(rule=rule, line_numbers=_line_numbers(docstring, line)))
    return tuple(findings)


def section_order_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for convention sections that appear out of order."""
    data = PDF_definition.PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        max_rank = -1
        for section in docstring.structure.sections:
            rank = _section_order_rank(docstring.structure.convention, section.name)
            if rank is None:
                continue
            if rank < max_rank:
                line = docstring.structure.lines[section.header_line]
                findings.append(RuleFinding(rule=rule, line_numbers=_line_numbers(docstring, line)))
            else:
                max_rank = rank
    return tuple(findings)


def repeated_section_findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for repeated convention sections."""
    data = PDF_definition.PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        seen_keys: set[str] = set()
        for section in docstring.structure.sections:
            key = _repeated_section_key(docstring.structure.convention, section.name)
            if key in seen_keys:
                line = docstring.structure.lines[section.header_line]
                findings.append(RuleFinding(rule=rule, line_numbers=_line_numbers(docstring, line)))
            else:
                seen_keys.add(key)
    return tuple(findings)


def colon_results(context: RuleContext, *, rule: RuleMetadata) -> tuple[SectionStyleResult, ...]:
    """Return findings and fixes for Google section names missing a colon."""
    data = PDF_definition.PDF.require_data(context)
    results: list[SectionStyleResult] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not settings_check.DocstringConvention.GOOGLE:
            continue
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        for section in docstring.structure.sections:
            line = docstring.structure.lines[section.header_line]
            if line.text.strip().endswith(":"):
                continue
            # Parsed Google section headers contain only the section name and optional trailing whitespace; PDF401
            # handles same-line section content.
            replacement = _replacement_for_section_suffix(line, section.name, ":")
            if replacement is None:
                unfixable_line_numbers.extend(_line_numbers(docstring, line))
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(_line_numbers(docstring, line))
            _replace_value_line_span(value_lines, line, replacement, ":")
        if not replacements and not unfixable_line_numbers:
            continue
        change = _planned_replacement_change(docstring, context=context, replacements=tuple(replacements), value_lines=value_lines)
        results.extend(_replacement_results(rule, replacement_line_numbers=replacement_line_numbers, unfixable_line_numbers=unfixable_line_numbers, change=change))
    return tuple(results)


def _result(rule: RuleMetadata, line_numbers: tuple[int, ...] | list[int], *, change: rule_edits.PlannedSourceChange | None) -> SectionStyleResult:
    return SectionStyleResult(finding=RuleFinding(rule=rule, line_numbers=tuple(dict.fromkeys(line_numbers)), instance_fixable=change is not None), change=change)


def _replacement_results(
    rule: RuleMetadata,
    *,
    replacement_line_numbers: list[int],
    unfixable_line_numbers: list[int],
    change: rule_edits.PlannedSourceChange | None,
) -> tuple[SectionStyleResult, ...]:
    if not replacement_line_numbers:
        return (_result(rule, unfixable_line_numbers, change=None),)
    if change is None:
        return (_result(rule, tuple(replacement_line_numbers) + tuple(unfixable_line_numbers), change=None),)
    results = [_result(rule, change.line_numbers, change=change)]
    if unfixable_line_numbers:
        results.append(_result(rule, unfixable_line_numbers, change=None))
    return tuple(results)


def _line_numbers(docstring: PDF_definition.DocstringInfo, line: PDF_definition.DocstringValueLine) -> tuple[int, ...]:
    return PDF_definition.docstring_line_numbers(docstring, line)


def _replacement_for_section_name(line: PDF_definition.DocstringValueLine, old_name: str, new_name: str) -> rule_edits.PlannedTextReplacement | None:
    start_column = _section_name_start_column(line)
    end_column = start_column + len(old_name)
    return _text_replacement(line, start_column, end_column, new_name)


def _replacement_for_section_suffix(line: PDF_definition.DocstringValueLine, name: str, suffix: str) -> rule_edits.PlannedTextReplacement | None:
    start_column = _section_name_start_column(line) + len(name)
    end_column = len(line.text)
    return _text_replacement(line, start_column, end_column, suffix)


def _text_replacement(line: PDF_definition.DocstringValueLine, start_column: int, end_column: int, text: str) -> rule_edits.PlannedTextReplacement | None:
    start_offset = PDF_definition.value_offset_for_text_column(line, start_column, require_source_text=True)
    end_offset = PDF_definition.value_offset_for_text_column(line, end_column, require_source_text=True)
    if start_offset is None or end_offset is None:
        return None
    return rule_edits.PlannedTextReplacement(start_offset=start_offset, end_offset=end_offset, text=text, line_numbers=PDF_definition.docstring_value_line_numbers((line,)))


def _section_name_start_column(line: PDF_definition.DocstringValueLine) -> int:
    return len(line.text) - len(line.text.lstrip(" \t"))


def _replace_value_line_span(value_lines: list[str], line: PDF_definition.DocstringValueLine, replacement: rule_edits.PlannedTextReplacement, text: str) -> None:
    raw_start_column = replacement.start_offset - line.start_offset
    raw_end_column = replacement.end_offset - line.start_offset
    value_lines[line.index] = f"{value_lines[line.index][:raw_start_column]}{text}{value_lines[line.index][raw_end_column:]}"


def _planned_replacement_change(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    replacements: tuple[rule_edits.PlannedTextReplacement, ...],
    value_lines: list[str],
) -> rule_edits.PlannedSourceChange | None:
    if not replacements or not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_source_change(docstring, context=context, replacements=replacements, value_lines=value_lines)


def _planned_output_change(
    docstring: PDF_definition.DocstringInfo,
    *,
    context: RuleContext,
    output_lines: tuple[PDF_definition.DocstringOutputLine, ...],
    line_numbers: tuple[int, ...],
) -> rule_edits.PlannedSourceChange | None:
    if not PDF_definition.is_safely_mapped_simple_docstring(docstring):
        return None
    return PDF_definition.planned_simple_docstring_output_change(docstring, context=context, output_lines=output_lines, line_numbers=line_numbers)


def _google_trailing_content_target(line: PDF_definition.DocstringValueLine, *, context: RuleContext) -> tuple[str, str] | None:
    match = _GOOGLE_TRAILING_CONTENT_RE.match(line.text)
    if match is None:
        return None
    name = match.group("name").rstrip()
    canonical = canonical_section_name(settings_check.DocstringConvention.GOOGLE, name)
    if canonical is None:
        return None
    raw_indent = line.raw_text[: line.text_raw_start_column + len(match.group("indent")) - line.text_virtual_prefix_length]
    header = f"{raw_indent}{name}:"
    content = f"{raw_indent}{PDF_definition.indent_unit(context.settings)}{match.group('content').strip()}"
    return header, content


def _protected_or_parsed_line_indexes(docstring: PDF_definition.DocstringInfo) -> set[int]:
    indexes: set[int] = set()
    for section in docstring.structure.sections:
        indexes.update(range(section.start_line, section.end_line))
    _add_protected_or_parsed_block_indexes(docstring.structure.blocks, indexes)
    return indexes


def _add_protected_or_parsed_block_indexes(blocks: tuple[PDF_definition.DocstringBlock, ...], indexes: set[int]) -> None:
    for block in blocks:
        if block.kind is not PDF_definition.DocstringBlockKind.PARAGRAPH:
            indexes.update(range(block.start_line, block.end_line))
            continue
        _add_protected_or_parsed_block_indexes(block.children, indexes)


def _target_underline(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> tuple[str | None, tuple[int, ...]]:
    header = docstring.structure.lines[section.header_line]
    underline = f"{header.raw_text[: header.text_raw_start_column + _section_name_start_column(header)]}{'-' * len(section.name)}"
    next_index = section.header_line + 1
    if next_index >= len(docstring.structure.lines):
        return underline, ()
    next_line = docstring.structure.lines[next_index]
    if PDF_definition.is_adornment(next_line.text):
        if next_line.text.strip() == "-" * len(section.name) and next_line.raw_text == underline:
            return None, ()
        return underline, (next_index,)
    scan_index = next_index
    while scan_index < section.end_line and not docstring.structure.lines[scan_index].text.strip():
        scan_index += 1
    if scan_index < section.end_line and PDF_definition.is_adornment(docstring.structure.lines[scan_index].text):
        return underline, tuple(range(next_index, scan_index + 1))
    return underline, ()


def _section_has_content(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> bool:
    return any(line.text.strip(" \t") for line in docstring.structure.lines[section.content_start_line : section.end_line])


def _section_order_rank(convention: settings_check.DocstringConvention, section_name: str) -> int | None:
    return PDF_definition.section_order_rank(convention, section_name)


def _repeated_section_key(convention: settings_check.DocstringConvention, section_name: str) -> str:
    return PDF_definition.repeated_section_key(convention, section_name)
