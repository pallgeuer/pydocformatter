"""PCF102 rule-codes-in-suppression-comments rule."""

# Future imports
from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definition_helpers import suppression_policies
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


if TYPE_CHECKING:
    # First-party imports
    import pydocformatter.rules.violations as rule_violations
    from pydocformatter.rules.definition import RuleContext


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF102RuleCodesInSuppressionComments(RuleBase):
    """Enforce rule names in bracketed pydocfmt and Ruff suppression comments.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF102"),
        name="rule-codes-in-suppression-comments",
        message="Suppression comment should use rule names instead of codes",
        fix_availability=FixAvailability.SOMETIMES,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(RuleCode("PCF103"),),
        check_kind=RuleCheckKind.STANDARD,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
        allows_directive_self_suppression=True,
    )

    @classmethod
    def violations(cls, context: RuleContext) -> tuple[rule_violations.RuleViolation, ...]:
        """Return name-policy violations for the current source.

        Args:
            context (RuleContext): Current source and prepared PCF directive data.

        Returns:
            tuple[rule_violations.RuleViolation, ...]: Fixable local code findings and diagnostic-only Ruff findings.
        """
        return suppression_policies.violations(context, rule=cls.meta, prefer_names=True)
