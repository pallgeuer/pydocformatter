"""PDF519 public-class-attribute-docstring-must-be-attached rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.attribute_documentation as attribute_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.cli.settings_check import DocstringConvention
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


@rule_registration.register_rule_to(PDF)
class PDF519PublicClassAttributeDocstringMustBeAttached(RuleBase):
    """Rule implementation for PDF519.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF519"),
        name="public-class-attribute-docstring-must-be-attached",
        message="Public class attribute must use attached docstring, not class docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(
            RuleSettingEffects(
                setting="docstring_convention",
                effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=(DocstringConvention.NONE, DocstringConvention.PEP257)),),
            ),
        ),
        incompatible_with=(RuleCode("PDF518"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for class docstrings documenting public attributes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return attribute_documentation.attribute_docstring_must_be_attached_violations(
            data, meta=cls.meta, owner_kind=PDF_definition.DefinitionKind.CLASS, owner_label="Class", public=True, include_instance=True
        )
