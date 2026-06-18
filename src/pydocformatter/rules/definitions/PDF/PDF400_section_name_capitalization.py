from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF400SectionNameCapitalization(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF400"),
        name="section-name-capitalization",
        message="Docstring section name should be properly capitalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for non-canonical convention section capitalization."""
        return section_edits.findings_for_results(_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Capitalize safely mapped convention section names."""
        return section_edits.fix_result_for_results(context, cls.meta, _results(context, rule=cls.meta))


def _results(context: RuleContext, *, rule: RuleMetadata) -> tuple[section_edits.SectionEditResult, ...]:
    """Return findings and fixes for section name capitalization."""
    data = PDF.require_data(context)
    results: list[section_edits.SectionEditResult] = []
    for docstring in data.docstrings:
        replacements: list[rule_edits.PlannedTextReplacement] = []
        value_lines = [line.raw_text for line in docstring.structure.lines]
        replacement_line_numbers: list[int] = []
        unfixable_line_numbers: list[int] = []
        replacement_messages: list[str] = []
        unfixable_messages: list[str] = []
        for section in docstring.structure.sections:
            canonical = docstring_sections.canonical_section_name(docstring.structure.convention, section.name)
            if canonical is None or canonical == section.name:
                continue
            message = f"Docstring section name '{section.name}' should be capitalized as '{canonical}'"
            line = docstring.structure.lines[section.header_line]
            replacement = section_edits.replacement_for_section_name(line, section.name, canonical)
            if replacement is None:
                unfixable_line_numbers.extend(section_edits.line_numbers(docstring, line))
                unfixable_messages.append(message)
                continue
            replacements.append(replacement)
            replacement_line_numbers.extend(section_edits.line_numbers(docstring, line))
            replacement_messages.append(message)
            section_edits.replace_value_line_span(value_lines, line, replacement, canonical)
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
