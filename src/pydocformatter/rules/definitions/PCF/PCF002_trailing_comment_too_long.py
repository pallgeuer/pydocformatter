from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PCF002TrailingCommentTooLong(RuleBase):
    meta = RuleMetadata(code=RuleCode("PCF002"), name="trailing-comment-too-long", message="Trailing comment needs formatting", fixable=True, stable_since="0.3.0")
