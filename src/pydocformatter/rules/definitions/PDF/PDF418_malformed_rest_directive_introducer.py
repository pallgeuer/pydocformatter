"""PDF418 malformed-rest-directive-introducer rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.violations as rule_violations
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import docstring_source
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata, RuleSettingEffect, RuleSettingEffects, RuleSettingEffectValues


if TYPE_CHECKING:
    # First-party imports
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PDF)
class PDF418MalformedRestDirectiveIntroducer(RuleBase):
    """Rule implementation for PDF418.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PDF418"),
        name="malformed-rest-directive-introducer",
        message="reST directive must be followed by two colons",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=(RuleSettingEffects(setting="docstring_parse_directives", effects=(RuleSettingEffectValues(effect=RuleSettingEffect.DISABLED, values=(False,)),)),),
        incompatible_with=(),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return violations for malformed reStructuredText directive introducers.

        Args:
            context (RuleContext): Current file context with parsed docstrings and prepared directive issues.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Rule violations reported for the current source.
        """
        data = PDF.require_data(context)
        return tuple(
            rule_violations.diagnostic(
                cls.meta,
                docstring_source.docstring_line_numbers(docstring, docstring.structure.lines[issue.start_line]),
                instance_message=f"reST directive '{issue.name}' must be followed by two colons",
            )
            for docstring in data.docstrings
            for issue in docstring.structure.directive_issues
        )
