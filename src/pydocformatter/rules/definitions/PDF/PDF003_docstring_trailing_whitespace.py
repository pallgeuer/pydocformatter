from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF003DocstringTrailingWhitespace(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF003"), name="docstring-trailing-whitespace", message="Non-empty docstring line has trailing whitespace", fixable=True, stable_since="0.3.0")
