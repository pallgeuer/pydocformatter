"""PDF305 summary-starts-with-this rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.summary_style as summary_style
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF305SummaryStartsWithThis(RuleBase):
    """Rule implementation for PDF305.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF305"),
        name="summary-starts-with-this",
        message='Docstring summary should not start with "This"',
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summaries whose first word is This."""
        data = PDF.require_data(context)
        violations: list[rule_violations.RuleViolation] = []
        for target in data.summary_line_targets:
            word = summary_style.first_word_target(target)
            if word is not None and summary_style.normalize_word(word.word) == "this":
                violations.append(rule_violations.diagnostic(cls.meta, summary_style.line_numbers(word)))
        return tuple(violations)
