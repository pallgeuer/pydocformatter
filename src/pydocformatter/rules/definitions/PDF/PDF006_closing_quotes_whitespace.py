from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF006ClosingQuotesWhitespace(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF006"), name="closing-quotes-whitespace", message="Docstring has extra whitespace before closing quotes", fixable=True, stable_since="0.3.0")
