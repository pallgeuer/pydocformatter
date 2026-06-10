from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.codes import RuleCode
from pydocformatter.rules.definition import RuleBase
from pydocformatter.rules.definitions.PDF.PDF import PDF
from pydocformatter.rules.models import FixAvailability, RuleMetadata


@rule_collection.register_rule_to(PDF)
class PDF004DocstringBlankLineWhitespace(RuleBase):
    meta = RuleMetadata(
        code=RuleCode("PDF004"),
        name="docstring-blank-line-whitespace",
        message="Blank docstring line has whitespace",
        fix_availability=FixAvailability.ALWAYS,
        stable_since="0.3.0",
        setting_effects=(),
    )
