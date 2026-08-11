"""PDF715 class-attribute-type-mismatch rule."""

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


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF715ClassAttributeTypeMismatch(RuleBase):
    """Rule implementation for PDF715.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata("PDF715", "class-attribute-type-mismatch", "Class attribute docstring type does not match the annotation", convention_opt_in=False, incompatible_with=("PDF714",))

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for class attribute docstring types that mismatch annotations.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.mismatch_violations(context, meta=cls.meta, subject=typed_models.TypedDocumentationSubject.CLASS_ATTRIBUTE, label="Class attribute")
