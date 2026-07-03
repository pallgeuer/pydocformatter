"""PDF308 entry-description-trailing-period rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.entry_description_style as entry_description_style
import pydocformatter.rules.definition_helpers.terminal_punctuation as terminal_punctuation
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues

_POLICY = terminal_punctuation.TerminalPunctuationPolicy(valid_endings=".", nonfixable_endings=",:;?!\u2026")


@rule_registration.register_rule_to(PDF)
class PDF308EntryDescriptionTrailingPeriod(RuleBase):
    """Rule implementation for PDF308.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF308"),
        name="entry-description-trailing-period",
        message="Docstring entry description should end with a period",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),),
            ),
        ),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for entry descriptions that do not end with a period.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return entry_description_style.punctuation_violations(context, rule=cls.meta, policy=_POLICY)
