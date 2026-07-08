"""PDF510 missing-public-module-attribute-documentation rule."""

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
class PDF510MissingPublicModuleAttributeDocumentation(RuleBase):
    """Rule implementation for PDF510.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF510"),
        name="missing-public-module-attribute-documentation",
        message="Public module attribute is missing docstring documentation",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(RuleSettingEffects(setting="docstring_convention", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.IGNORED, values=tuple(DocstringConvention)),)),),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for module attributes missing documentation.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return attribute_documentation.missing_attribute_violations(
            data, context=context, meta=cls.meta, owner_kind=PDF_definition.DefinitionKind.MODULE, owner_label="Public module", include_instance=False
        )
