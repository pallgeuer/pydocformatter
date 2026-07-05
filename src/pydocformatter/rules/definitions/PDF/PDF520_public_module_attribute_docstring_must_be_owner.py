"""PDF520 public-module-attribute-docstring-must-be-owner rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.attribute_documentation as attribute_documentation
import pydocformatter.rules.definitions.PDF.PDF as PDF_definition
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PDF)
class PDF520PublicModuleAttributeDocstringMustBeOwner(RuleBase):
    """Rule implementation for PDF520.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF520"),
        name="public-module-attribute-docstring-must-be-owner",
        message="Public module attribute must use module docstring documentation, not attached docstring",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(RuleCode("PDF521"),),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for attached docstrings on public module attributes.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return attribute_documentation.attribute_docstring_must_be_owner_violations(
            data, meta=cls.meta, owner_kind=PDF_definition.DefinitionKind.MODULE, owner_label="Module", public=True, include_instance=False
        )
