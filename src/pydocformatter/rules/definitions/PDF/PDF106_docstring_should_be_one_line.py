from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF106DocstringShouldBeOneLine(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF106"), name="docstring-should-be-one-line", message="Docstring with one content line should be one line", fixable=True, stable_since="0.3.0")
