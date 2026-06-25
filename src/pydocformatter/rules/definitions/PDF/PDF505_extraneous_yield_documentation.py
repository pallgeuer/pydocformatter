"""PDF505 extraneous-yield-documentation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.docstring_conventions as docstring_conventions
import pydocformatter.rules.definition_helpers.value_documentation as value_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF505ExtraneousYieldDocumentation(RuleBase):
    """Rule implementation for PDF505.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF505"),
        name="extraneous-yield-documentation",
        message="Docstring has a yield section for a function that does not yield a meaningful value",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(
                        effect=RuleSettingEffect.IGNORED, values=docstring_conventions.ignored_conventions_except(DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.REST)
                    ),
                ),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for yield docs on functions without meaningful yields."""
        findings: list[RuleFinding] = []
        for definition, docstring, facts in value_documentation.documented_function_facts(context):
            del definition
            if facts.meaningful_yields:
                continue
            for entry in value_documentation.value_documentation_targets(docstring, PDF_definition.DocstringEntryKind.YIELD):
                if facts.explicit_none_yields and entry.has_content:
                    continue
                findings.append(RuleFinding(rule=cls.meta, line_numbers=entry.line_numbers))
        return tuple(findings)
