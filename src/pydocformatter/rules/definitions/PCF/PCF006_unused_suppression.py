"""PCF006 unused-suppression rule."""

from __future__ import annotations

import pydocformatter.rules.definitions.PCF.PCF as PCF_definition
import pydocformatter.rules.registration as rule_registration
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.models import FixAvailability, RuleCheckKind, RuleMetadata


@rule_registration.register_rule_to(PCF_definition.PCF)
class PCF006UnusedSuppression(RuleBase):
    """Rule implementation for PCF006.

    Attributes:
        meta (RuleMetadata): Static metadata used for registration, diagnostics, and rule selection.
    """

    meta = RuleMetadata(
        code=RuleCode("PCF006"),
        name="unused-suppression",
        message="Suppression directive is unused",
        fix_availability=FixAvailability.NEVER,
        stable_since="1.0.0",
        setting_effects=(),
        incompatible_with=(),
        check_kind=RuleCheckKind.SUPPRESSION_AUDIT,
    )
