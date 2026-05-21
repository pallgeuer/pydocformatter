from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF100TooManyBlankLines(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF100"), name="too-many-blank-lines", message="Docstring has too many blank lines", fixable=True, stable_since="0.3.0")
