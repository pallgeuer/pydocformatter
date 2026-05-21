from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF004DocstringBlankLineWhitespace(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF004"), name="docstring-blank-line-whitespace", message="Blank docstring line has whitespace", fixable=True, stable_since="0.3.0")
