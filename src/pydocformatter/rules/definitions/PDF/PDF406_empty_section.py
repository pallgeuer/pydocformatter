from __future__ import annotations

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
class PDF406EmptySection(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF406"),
        name="empty-section",
        message="Docstring section should not be empty",
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
        """Return findings for recognized sections without body content."""
        return _findings(context, rule=cls.meta)


def _findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for recognized sections or reST fields with no body content."""
    data = PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        for section in docstring.structure.sections:
            if not _section_has_content(docstring, section):
                line = docstring.structure.lines[section.header_line]
                findings.append(
                    RuleFinding(
                        rule=rule,
                        line_numbers=section_edits.line_numbers(docstring, line),
                        instance_message=f"Docstring section '{section.name}' should not be empty",
                    )
                )
        if docstring.structure.convention is DocstringConvention.REST:
            for entry in docstring.structure.entries:
                if entry.field_name is None or rest_fields.has_content(entry):
                    continue
                line = docstring.structure.lines[entry.start_line]
                findings.append(
                    RuleFinding(
                        rule=rule,
                        line_numbers=section_edits.line_numbers(docstring, line),
                        instance_message=f"Docstring field '{rest_fields.label(entry)}' should not be empty",
                    )
                )
    return tuple(findings)


def _section_has_content(docstring: PDF_definition.DocstringInfo, section: PDF_definition.DocstringSection) -> bool:
    return any(line.text.strip(" \t") for line in docstring.structure.lines[section.content_start_line : section.end_line])
