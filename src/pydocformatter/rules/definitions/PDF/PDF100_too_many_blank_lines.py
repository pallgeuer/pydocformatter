from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata
from pydocformatter.rules.definitions.PDF.PDF import PDF


@rule_collection.register_rule_to(PDF)
class PDF100TooManyBlankLines(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF100"), name="too-many-blank-lines", message="Docstring has too many blank lines", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
