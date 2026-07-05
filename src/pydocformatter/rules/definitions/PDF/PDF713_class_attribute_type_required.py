"""PDF713 class-attribute-type-required rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.typed_entry_rules as typed_entry_rules
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_registration.register_rule_to(PDF)
class PDF713ClassAttributeTypeRequired(RuleBase):
    """Rule implementation for PDF713.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata("PDF713", "class-attribute-type-required", "Class attribute docstring entry is missing a type", exact_opt_in=True, incompatible_with=("PDF714",))

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for class attribute docstring type policy.

        Args:
            context (RuleContext): Current file context with parsed docstrings, prepared PDF data, and enum-base
                settings.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.required_type_violations(context, meta=cls.meta, subject=typed_entry_rules.TypedDocumentationSubject.CLASS_ATTRIBUTE, label="Class attribute")
