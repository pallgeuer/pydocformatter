from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF106DocstringShouldBeOneLine(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF106"), name="docstring-should-be-one-line", message="Docstring with one content line should be one line", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0"
    )
