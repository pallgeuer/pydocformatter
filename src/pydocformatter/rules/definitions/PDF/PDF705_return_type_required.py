"""PDF705 return-type-required rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definition_helpers.typed_documentation_models as typed_models
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import typed_entry_rules
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF705ReturnTypeRequired(RuleBase):
    """Rule implementation for PDF705.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata(
        "PDF705", "return-type-required", "Function return docstring entry is missing a type", convention_opt_in=True, incompatible_with=("PDF706",), fix_availability=FixAvailability.SOMETIMES
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for return docstring entries missing types.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.required_type_violations(context, meta=cls.meta, subject=typed_models.TypedDocumentationSubject.RETURN, label="Function return")
