from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import FixAvailability, RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF004DocstringBlankLineWhitespace(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF004"), name="docstring-blank-line-whitespace", message="Blank docstring line has whitespace", fix_availability=FixAvailability.ALWAYS, stable_since="0.3.0")
