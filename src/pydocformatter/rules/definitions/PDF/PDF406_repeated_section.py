from __future__ import annotations

import pydocformatter.rules.definition_helpers.section_style as section_style
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
        stable_since="0.3.0",
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
        return section_style.repeated_section_findings(context, rule=cls.meta)
