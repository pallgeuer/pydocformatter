from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF005OpeningQuotesWhitespace(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF005"), name="opening-quotes-whitespace", message="Docstring has extra whitespace after opening quotes", fixable=True, stable_since="0.3.0")
