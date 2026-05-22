from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF104MultilineClosingQuotesSepLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF104"),
        name="multiline-closing-quotes-sep-line",
        message="Multi-line docstring closing quotes should be on a separate line",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
    )
