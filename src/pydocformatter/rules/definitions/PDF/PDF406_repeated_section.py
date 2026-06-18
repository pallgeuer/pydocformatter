from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_sections as docstring_sections
import pydocformatter.rules.definition_helpers.rest_fields as rest_fields
import pydocformatter.rules.definition_helpers.section_edits as section_edits
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF406RepeatedSection(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF406"),
        name="repeated-section",
        message="Docstring section should not be repeated",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for repeated convention sections."""
        return _findings(context, rule=cls.meta)


def _findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for repeated convention sections or rest fields."""
    data = PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is DocstringConvention.REST:
            findings.extend(_rest_field_findings(docstring, rule=rule))
        else:
            seen_keys: dict[str, str] = {}
            for section in docstring.structure.sections:
                key = docstring_sections.repeated_section_key(docstring.structure.convention, section.name)
                if key in seen_keys:
                    line = docstring.structure.lines[section.header_line]
                    findings.append(
                        RuleFinding(
                            rule=rule,
                            line_numbers=section_edits.line_numbers(docstring, line),
                            instance_message=f"Docstring section '{section.name}' repeats earlier section '{seen_keys[key]}'",
                        )
                    )
                else:
                    seen_keys[key] = section.name
    return tuple(findings)


def _rest_field_findings(docstring: PDF_definition.DocstringInfo, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    findings: list[RuleFinding] = []
    seen_keys: dict[tuple[str, str, str], str] = {}
    for entry in docstring.structure.entries:
        if entry.field_name is None:
            continue
        key = rest_fields.repetition_key(entry)
        if key is None:
            continue
        label = rest_fields.label(entry)
        if key in seen_keys:
            line = docstring.structure.lines[entry.start_line]
            findings.append(
                RuleFinding(
                    rule=rule,
                    line_numbers=section_edits.line_numbers(docstring, line),
                    instance_message=f"Docstring field '{label}' repeats earlier field '{seen_keys[key]}'",
                )
            )
        else:
            seen_keys[key] = label
    return tuple(findings)
