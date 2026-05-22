from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF005OpeningQuotesWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF005"), name="opening-quotes-whitespace", message="Docstring has extra whitespace after opening quotes", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0"
    )
