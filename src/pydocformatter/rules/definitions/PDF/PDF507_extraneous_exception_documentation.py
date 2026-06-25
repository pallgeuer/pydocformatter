"""PDF507 extraneous-exception-documentation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF507ExtraneousExceptionDocumentation(RuleBase):
    """Rule implementation for PDF507.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF507"),
        name="extraneous-exception-documentation",
        message="Docstring documents an exception that is not explicitly raised",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED,
                        values=(DocstringConvention.NONE, DocstringConvention.PEP257, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST),
                    ),
                ),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for exception docs absent from direct raises."""
        findings: list[RuleFinding] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            del definition
            for entry in value_documentation.documented_entries(docstring, PDF_definition.DocstringEntryKind.EXCEPTION, require_content=False):
                if entry.name is not None and not any(value_documentation.exception_names_match(raised.name, entry.name) for raised in facts.raised_exceptions):
                    findings.append(RuleFinding(rule=cls.meta, line_numbers=entry.line_numbers, instance_message=f"Docstring documents exception '{entry.name}' that is not explicitly raised"))
        return tuple(findings)
