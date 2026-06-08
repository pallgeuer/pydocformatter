from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleCode, RuleMetadata


@rule_collection.register_rule_to(PDF)
class PDF103MultilineClosingQuotesSameLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF103"),
        name="multiline-closing-quotes-same-line",
        message="Multi-line docstring closing quotes should be on the same line as content",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )
