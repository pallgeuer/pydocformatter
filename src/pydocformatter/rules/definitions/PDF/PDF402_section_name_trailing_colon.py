from __future__ import annotations

import pydocformatter.rules.definition_helpers.section_style as section_style
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF402SectionNameTrailingColon(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF402"),
        name="section-name-trailing-colon",
        message="Docstring section name should end with a colon",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=section_style.GOOGLE_IGNORED_CONVENTIONS),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for Google section names missing a trailing colon."""
        return section_style.findings_for_results(section_style.colon_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Add safe missing Google section-name colons."""
        return section_style.fix_result_for_results(context, cls.meta, section_style.colon_results(context, rule=cls.meta))
