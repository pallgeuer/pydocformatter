"""PDF205 blank-line-before-function-docstring rule."""

from __future__ import annotations

import pydocformatter.cli.settings_check as settings_check
import pydocformatter.rules.definition_helpers.docstring_statement_spacing as docstring_statement_spacing
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF205BlankLineBeforeFunctionDocstring(RuleBase):
    """Rule implementation for PDF205.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF205"),
        name="blank-line-before-function-docstring",
        message="One blank line required before function docstring",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(settings_check.DocstringConvention)),),
            ),
        ),
        incompatible_with=(RuleCode("PDF204"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for missing or excess blank lines before function docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        changes = docstring_statement_spacing.planned_changes(
            context,
            owner_kind=PDF_definition.DefinitionKind.FUNCTION,
            position=docstring_statement_spacing.DocstringStatementSpacingPosition.BEFORE,
            desired_blank_lines=1,
        )
        return rule_violations.violations_for_planned_source_changes(cls.meta, changes)
