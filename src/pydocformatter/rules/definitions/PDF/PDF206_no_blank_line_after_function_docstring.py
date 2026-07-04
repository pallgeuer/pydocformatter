"""PDF206 no-blank-line-after-function-docstring rule."""

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
class PDF206NoBlankLineAfterFunctionDocstring(RuleBase):
    """Rule implementation for PDF206.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF206"),
        name="no-blank-line-after-function-docstring",
        message="No blank lines allowed after function docstring",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(settings_check.DocstringConvention)),),
            ),
        ),
        incompatible_with=(RuleCode("PDF207"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for blank lines after function docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        changes = docstring_statement_spacing.planned_changes(
            context,
            owner_kind=PDF_definition.DefinitionKind.FUNCTION,
            position=docstring_statement_spacing.DocstringStatementSpacingPosition.AFTER,
            desired_blank_lines=0,
        )
        return rule_violations.violations_for_planned_source_changes(cls.meta, changes)
