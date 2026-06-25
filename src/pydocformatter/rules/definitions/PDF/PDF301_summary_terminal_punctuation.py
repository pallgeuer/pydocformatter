"""PDF301 summary-terminal-punctuation rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.summary_punctuation as summary_punctuation
import pydocformatter.rules.edits as rule_edits
import pydocformatter.rules.registration as rule_registration
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext, RuleFixResult
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleFinding, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues

_POLICY = summary_punctuation.SummaryPunctuationPolicy(valid_endings=".?!\u2026", nonfixable_endings=",:;")


@rule_registration.register_rule_to(PDF)
class PDF301SummaryTerminalPunctuation(RuleBase):
    """Rule implementation for PDF301.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF301"),
        name="summary-terminal-punctuation",
        message="Docstring summary should end with terminal punctuation",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NUMPY, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(),
    )

    @classmethod
    def check(cls, context: RuleContext) -> tuple[RuleFinding, ...]:
        """Return findings for summaries that do not end with terminal punctuation."""
        return tuple(result.finding for result in summary_punctuation.results(context, rule=cls.meta, policy=_POLICY))

    @classmethod
    def fix(cls, context: RuleContext) -> RuleFixResult:
        """Insert safe missing summary terminal punctuation."""
        changes = tuple(result.change for result in summary_punctuation.results(context, rule=cls.meta, policy=_POLICY) if result.change is not None)
        if not changes:
            return RuleFixResult(module=context.module)
        module = rule_edits.apply_context_source_changes(context, changes)
        findings = rule_edits.findings_for_planned_source_changes(cls.meta, changes, instance_fixable=True)
        return RuleFixResult(module=module, fixed_findings=findings)
