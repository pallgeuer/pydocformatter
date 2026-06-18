from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF403SectionUnderlineFormat(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF403"),
        name="section-underline-format",
        message="Docstring section underline should be normalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.NUMPY)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for malformed NumPy section underlines."""
        return section_edits.findings_for_results(_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Normalize safely mapped NumPy section underlines."""
        return section_edits.fix_result_for_results(context, cls.meta, _results(context, rule=cls.meta))


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[section_edits.SectionEditResult, ...]:
    """Return findings and fixes for NumPy section underlines."""
    data = PDF.require_data(context)
    results: list[section_edits.SectionEditResult] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not DocstringConvention.NUMPY:
            continue
        output_lines: list[PDF_definition.DocstringOutputLine] = []
        line_numbers: list[int] = []
        messages: list[str] = []
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
            line_numbers.extend(section_edits.line_numbers(docstring, line))
            messages.append(f"Docstring section '{section.name}' underline should be normalized")
            output_lines.append(PDF_definition.DocstringOutputLine(source=underline, value=underline))
            skip_indexes.update(skipped)
            changed = True
        if not changed:
            continue
        change = section_edits.planned_output_change(docstring, context=context, output_lines=tuple(output_lines), line_numbers=tuple(line_numbers))
        results.append(section_edits.result(rule, line_numbers, change=change, instance_message=section_edits.combined_instance_message(messages)))
    return tuple(results)


def _target_underline(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> tuple[str | None, tuple[int, ...]]:
    header = docstring.structure.lines[section.header_line]
    underline = f"{header.raw_text[: header.text_raw_start_column + section_edits.section_name_start_column(header)]}{'-' * len(section.name)}"
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
