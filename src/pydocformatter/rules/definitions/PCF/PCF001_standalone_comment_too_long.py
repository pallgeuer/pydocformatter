from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PCF001StandaloneCommentTooLong(RuleBase):
    meta = RuleMetadata(code=RuleCode("PCF001"), name="standalone-comment-too-long", message="Standalone comment needs formatting", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
