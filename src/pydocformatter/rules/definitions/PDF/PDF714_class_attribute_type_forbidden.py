"""PDF714 class-attribute-type-forbidden rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.typed_entry_rules as typed_entry_rules
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_registration.register_rule_to(PDF)
class PDF714ClassAttributeTypeForbidden(RuleBase):
    """Rule implementation for PDF714.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata(
        "PDF714", "class-attribute-type-forbidden", "Class attribute docstring entry should not include a type", exact_opt_in=True, incompatible_with=("PDF713", "PDF715")
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for class attribute docstring entries with types.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.forbidden_type_violations(context, meta=cls.meta, subject=typed_entry_rules.TypedDocumentationSubject.CLASS_ATTRIBUTE, label="Class attribute")
