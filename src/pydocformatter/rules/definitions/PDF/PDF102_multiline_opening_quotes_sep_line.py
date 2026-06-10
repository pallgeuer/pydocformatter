from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_collection.register_rule_to(PDF)
class PDF102MultilineOpeningQuotesSepLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF102"),
        name="multiline-opening-quotes-sep-line",
        message="Multi-line docstring opening quotes should be on a separate line",
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
        incompatible_with=(RuleCode("PDF101"),),
    )
