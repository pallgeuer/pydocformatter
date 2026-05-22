from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF105SummaryTooLong(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF105"), name="summary-too-long", message="Docstring summary does not fit on one line", fix_availability=FixAvailability.NEVER, stable_since="0.3.0")
