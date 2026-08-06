"""PDF405 section-underline-format rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, docstring_rendering, docstring_source, section_edits
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF405SectionUnderlineFormat(RuleBase):
    """Rule implementation for PDF405.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF405"),
        name="section-underline-format",
        message="Docstring section underline should be normalized",
        fix_availability=FixAvailability.USUALLY,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=docstring_conventions.conventions_except(DocstringConvention.NUMPY)),)
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for malformed NumPy section underlines.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return _results(context, rule=cls.meta)


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[rule_violations.RuleViolation, ...]:
    """Return violations for NumPy section underlines."""
    data = PDF.require_data(context)
    results: list[rule_violations.RuleViolation] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is not DocstringConvention.NUMPY:
            continue
        output_lines: list[docstring_rendering.DocstringOutputLine] = []
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
                output_lines.append(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None))
                continue
            output_lines.append(docstring_rendering.DocstringOutputLine(original=line, source=None, value=None))
            underline, skipped = _target_underline(docstring, section)
            if underline is None:
                continue
            line_numbers.extend(section_edits.line_numbers(docstring, line))
            messages.append(f"Docstring section '{section.name}' underline should be normalized")
            output_lines.append(docstring_rendering.DocstringOutputLine(source=underline, value=underline))
            skip_indexes.update(skipped)
            changed = True
        if not changed:
            continue
        change = section_edits.planned_output_change(docstring, context=context, output_lines=tuple(output_lines), line_numbers=tuple(line_numbers))
        results.append(section_edits.result(rule, line_numbers, change=change, instance_message=section_edits.combined_instance_message(messages)))
    return tuple(results)


def _target_underline(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> tuple[str | None, tuple[int, ...]]:
    """Return the canonical NumPy underline and existing underline lines to replace."""
    header = docstring.structure.lines[section.header_line]
    prefix_end = docstring_source.value_offset_for_text_column(header, section_edits.section_name_start_column(header)) - header.start_offset
    underline = f"{header.raw_text[:prefix_end]}{'-' * len(section.name)}"
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
