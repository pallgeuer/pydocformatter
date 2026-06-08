from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF101MultilineOpeningQuotesSameLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF101"),
        name="multiline-opening-quotes-same-line",
        message="Multi-line docstring opening quotes should be on the same line as content",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )
