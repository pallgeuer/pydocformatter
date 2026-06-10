from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata


@rule_collection.register_rule_to(PDF)
class PDF005OpeningQuotesWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF005"),
        name="opening-quotes-whitespace",
        message="Docstring has extra whitespace after opening quotes",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
        incompatible_with=(),
    )
