from __future__ import annotations

import pydocformatter.rules.definition_helpers.section_style as section_style
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF401SectionNameTrailingContent(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF401"),
        name="section-name-trailing-content",
        message="Docstring section name should be followed by a line break",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="0.3.0",
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
        """Return findings for section names with content on the same line."""
        return section_style.findings_for_results(section_style.trailing_content_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Move same-line Google section content below the section name."""
        return section_style.fix_result_for_results(context, cls.meta, section_style.trailing_content_results(context, rule=cls.meta))
