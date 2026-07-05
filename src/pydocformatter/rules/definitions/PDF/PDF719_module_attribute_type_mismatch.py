"""PDF719 module-attribute-type-mismatch rule."""

from __future__ import annotations

import pydocformatter.rules.definition_helpers.typed_entry_rules as typed_entry_rules
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.violations as rule_violations
from pydocformatter.rules.definition import RuleBase, RuleContext
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_registration.register_rule_to(PDF)
class PDF719ModuleAttributeTypeMismatch(RuleBase):
    """Rule implementation for PDF719.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata("PDF719", "module-attribute-type-mismatch", "Module attribute docstring type does not match the annotation", exact_opt_in=False, incompatible_with=("PDF718",))

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for module attribute docstring types that mismatch annotations.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.mismatch_violations(context, meta=cls.meta, subject=typed_entry_rules.TypedDocumentationSubject.MODULE_ATTRIBUTE, label="Module attribute")
