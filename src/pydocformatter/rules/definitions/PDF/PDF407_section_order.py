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
class PDF407SectionOrder(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF407"),
        name="section-order",
        message="Docstring sections should be in the configured order",
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
        """Return findings for convention sections that appear out of order."""
        return _findings(context, rule=cls.meta)


def _findings(context: RuleContext, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    """Return findings for convention sections or reST fields that appear out of order."""
    data = PDF.require_data(context)
    findings: list[RuleFinding] = []
    for docstring in data.docstrings:
        if docstring.structure.convention is DocstringConvention.REST:
            findings.extend(_rest_field_findings(docstring, rule=rule))
        else:
            max_rank = -1
            max_rank_section_name = ""
            for section in docstring.structure.sections:
                rank = docstring_sections.section_order_rank(docstring.structure.convention, section.name)
                if rank is None:
                    continue
                if rank < max_rank:
                    line = docstring.structure.lines[section.header_line]
                    findings.append(
                        RuleFinding(
                            rule=rule,
                            line_numbers=section_edits.line_numbers(docstring, line),
                            instance_message=f"Docstring section '{section.name}' should appear before '{max_rank_section_name}'",
                        )
                    )
                else:
                    max_rank = rank
                    max_rank_section_name = section.name
    return tuple(findings)


def _rest_field_findings(docstring: PDF_definition.DocstringInfo, *, rule: RuleMetadata) -> tuple[RuleFinding, ...]:
    findings: list[RuleFinding] = []
    max_rank = -1
    max_rank_label = ""
    for entry in docstring.structure.entries:
        if entry.field_name is None:
            continue
        rank = rest_fields.order_rank(entry)
        if rank is None:
            continue
        label = rest_fields.label(entry)
        if rank < max_rank:
            line = docstring.structure.lines[entry.start_line]
            findings.append(
                RuleFinding(
                    rule=rule,
                    line_numbers=section_edits.line_numbers(docstring, line),
                    instance_message=f"Docstring field '{label}' should appear before '{max_rank_label}'",
                )
            )
        else:
            max_rank = rank
            max_rank_label = label
    return tuple(findings)
