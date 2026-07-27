"""PDF300 summary-trailing-period rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import summary_terminal_punctuation, terminal_punctuation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF300SummaryTrailingPeriod(RuleBase):
    """Rule implementation for PDF300.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF300"),
        name="summary-trailing-period",
        message="Docstring summary should end with a period",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.GOOGLE,)),)),),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for summaries that do not end with a period.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return summary_terminal_punctuation.results(context, rule=cls.meta, policy=terminal_punctuation.TRAILING_PERIOD_POLICY)
