from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PCF.PCF import PCF
from pydocformatter.rules.models import FixAvailability, RuleCode, RuleMetadata


@rule_collection.register_rule_to(PCF)
class PCF001StandaloneCommentTooLong(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PCF001"),
        name="standalone-comment-too-long",
        message="Standalone comment needs formatting",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )
