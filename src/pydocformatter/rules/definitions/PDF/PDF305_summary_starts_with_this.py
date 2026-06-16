from __future__ import annotations

import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF305SummaryStartsWithThis(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF305"),
        name="summary-starts-with-this",
        message='Docstring summary should not start with "This"',
        fix_availability=FixAvailability.NEVER,
        stable_since="0.3.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for summaries whose first word is This."""
        data = PDF.require_data(context)
        findings: list[RuleFinding] = []
        for target in data.summary_line_targets:
            word = summary_style.first_word_target(target)
            if word is not None and summary_style.normalize_word(word.word) == "this":
                findings.append(RuleFinding(rule=cls.meta, line_numbers=summary_style.line_numbers(word)))
        return tuple(findings)
