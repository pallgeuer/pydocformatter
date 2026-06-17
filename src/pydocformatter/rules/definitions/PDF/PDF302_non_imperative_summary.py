from __future__ import annotations

import pydocformatter.rules.definition_helpers.imperative_mood as imperative_mood
import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF302NonImperativeSummary(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF302"),
        name="non-imperative-summary",
        message="Docstring summary should be in imperative mood",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for function summaries that are not imperative."""
        data = PDF.require_data(context)
        findings: list[RuleFinding] = []
        for target in data.summary_line_targets:
            if not summary_style.is_function_docstring(target.docstring) or summary_style.is_test_function(target.docstring) or summary_style.is_property_function(target.docstring):
                continue
            word = summary_style.first_word_target(target)
            if word is None:
                continue
            normalized = summary_style.normalize_word(word.word)
            if normalized and imperative_mood.is_non_imperative(normalized):
                findings.append(RuleFinding(rule=cls.meta, line_numbers=summary_style.line_numbers(word), instance_message=f"Docstring summary first word '{word.word}' is not imperative"))
        return tuple(findings)
