from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF103MultilineClosingQuotesSameLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF103"), name="multiline-closing-quotes-same-line", message="Multi-line docstring closing quotes should be on the same line as content", fixable=True, stable_since="0.3.0"
    )
