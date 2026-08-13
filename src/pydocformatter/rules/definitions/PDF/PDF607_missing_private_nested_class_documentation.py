"""PDF607 missing-private-nested-class-documentation rule."""

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
from pydocformatter.rules.models import MODULE_SOURCE_CONTEXTS, FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF607MissingPrivateNestedClassDocumentation(RuleBase):
    """Rule implementation for PDF607.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF607"),
        name="missing-private-nested-class-documentation",
        message="Private nested class is missing docstring",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
        source_contexts=MODULE_SOURCE_CONTEXTS,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for private nested classes missing docstrings.

        Args:
            context (RuleContext): Current file context with parsed module, settings, and prepared category data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return owner_documentation.missing_owner_docstring_violations(
            PDF.require_data(context), context=context, meta=cls.meta, policy=owner_documentation.MissingOwnerDocumentationPolicy(entity="nested-class", public=False)
        )
