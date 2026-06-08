from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF006ClosingQuotesWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF006"), name="closing-quotes-whitespace", message="Docstring has extra whitespace before closing quotes", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0"
    )
