from __future__ import annotations

import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF104MultilineClosingQuotesSameLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF104"),
        name="multiline-closing-quotes-same-line",
        message="Multi-line docstring closing quotes should be on the same line as content",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(
                    RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.GOOGLE, DocstringConvention.NUMPY, DocstringConvention.PEP257)),
                ),
            ),
        ),
        incompatible_with=(RuleCode("PDF105"),),
    )
