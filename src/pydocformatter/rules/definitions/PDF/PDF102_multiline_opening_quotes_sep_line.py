from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF102MultilineOpeningQuotesSepLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF102"),
        name="multiline-opening-quotes-sep-line",
        message="Multi-line docstring opening quotes should be on a separate line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )
