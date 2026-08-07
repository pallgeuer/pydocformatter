"""PCF101 unused-suppression rule."""

# Future imports
from __future__ import annotations

# First-party imports
import pydocformatter.rules.registration as rule_registration
import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.models import FixAvailability, RuleCacheBehavior, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF101UnusedSuppression(RuleBase):
    """Rule implementation for PCF101.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF101"),
        name="unused-suppression",
        message="Suppression selector is invalid, unknown, or unused",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.1.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.SUPPRESSION_AUDIT,
        cache_behavior=RuleCacheBehavior.FILE_LOCAL,
    )
