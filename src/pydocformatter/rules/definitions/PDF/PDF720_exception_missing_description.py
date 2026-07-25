"""PDF720 exception-missing-description rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_conventions, entry_completeness
from pydocformatter.rules.definitions.PDF.PDF import PDF, DocstringEntryKind
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF720ExceptionMissingDescription(RuleBase):
    """Rule implementation for PDF720.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF720"),
        name="exception-missing-description",
        message="Exception docstring entry is missing a description",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=docstring_conventions.convention_setting_effects(disabled=docstring_conventions.UNPARSED_CONVENTIONS),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for exception entries missing descriptions.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared PDF data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        return entry_completeness.missing_raw_entry_description_violations(context, meta=cls.meta, kind=DocstringEntryKind.EXCEPTION, label="Exception")
