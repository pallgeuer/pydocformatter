from __future__ import annotations

import pydocformatter.rules.collection as rule_collection
from pydocformatter.rules.base import RuleBase, RuleCode, RuleMetadata


@rule_collection.register_rule
class PDF002IncorrectIndentation(RuleBase):
    meta = RuleMetadata(code=RuleCode("PDF002"), name="incorrect-indentation", message="Docstring line is incorrectly indented", fixable=True, stable_since="0.3.0")
