from __future__ import annotations

import pydocformatter.rules.definition_helpers.section_style as section_style
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF403SectionUnderlineFormat(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF403"),
        name="section-underline-format",
        message="Docstring section underline should be normalized",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=section_style.NUMPY_IGNORED_CONVENTIONS),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for malformed NumPy section underlines."""
        return section_style.findings_for_results(section_style.underline_results(context, rule=cls.meta))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Normalize safely mapped NumPy section underlines."""
        return section_style.fix_result_for_results(context, cls.meta, section_style.underline_results(context, rule=cls.meta))
