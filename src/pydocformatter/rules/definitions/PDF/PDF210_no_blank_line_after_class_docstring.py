"""PDF210 no-blank-line-after-class-docstring rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli import settings_check
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_statement_spacing
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF_definition.PDF)
class PDF210NoBlankLineAfterClassDocstring(RuleBase):
    """Rule implementation for PDF210.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF210"),
        name="no-blank-line-after-class-docstring",
        message="No blank lines allowed after class docstring",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="1.0.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(settings_check.DocstringConvention)),)),),
        incompatible_with=(RuleCode("PDF211"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for blank lines after class docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        changes = docstring_statement_spacing.planned_changes(
            context, owner_kind=PDF_definition.DefinitionKind.CLASS, position=docstring_statement_spacing.DocstringStatementSpacingPosition.AFTER, desired_blank_lines=0
        )
        return rule_violations.violations_for_planned_source_changes(cls.meta, changes)
