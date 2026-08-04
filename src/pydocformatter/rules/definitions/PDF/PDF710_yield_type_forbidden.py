"""PDF710 yield-type-forbidden rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import typed_entry_rules
from pydocformatter.rules.definitions.PDF.PDF import PDF


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF710YieldTypeForbidden(RuleBase):
    """Rule implementation for PDF710.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = typed_entry_rules.metadata("PDF710", "yield-type-forbidden", "Function yield docstring entry should not include a type", convention_opt_in=True, incompatible_with=("PDF709", "PDF711"))

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for yield docstring entries with types.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return typed_entry_rules.forbidden_type_violations(context, meta=cls.meta, subject=typed_entry_rules.TypedDocumentationSubject.YIELD, label="Function yield")
