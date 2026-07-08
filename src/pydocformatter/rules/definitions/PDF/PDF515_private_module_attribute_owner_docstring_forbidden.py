"""PDF515 private-module-attribute-owner-docstring-forbidden rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import attribute_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF515PrivateModuleAttributeOwnerDocstringForbidden(RuleBase):
    """Rule implementation for PDF515.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF515"),
        name="private-module-attribute-owner-docstring-forbidden",
        message="Module docstring documents a private attribute",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),)),
        ),
        incompatible_with=(RuleCode("PDF524"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for module docstrings documenting private attributes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return attribute_documentation.private_owner_attribute_violations(data, meta=cls.meta, owner_kind=PDF_definition.DefinitionKind.MODULE, owner_label="Module")
