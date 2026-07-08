"""PDF612 missing-public-dunder-method-documentation rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import owner_documentation
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF612MissingPublicDunderMethodDocumentation(RuleBase):
    """Rule implementation for PDF612.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF612"),
        name="missing-public-dunder-method-documentation",
        message="Public dunder method is missing docstring",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for public dunder methods missing docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return owner_documentation.missing_owner_docstring_violations(
            PDF.require_data(context), context=context, meta=cls.meta, policy=owner_documentation.MissingOwnerDocumentationPolicy(entity="dunder-method", public=True)
        )
